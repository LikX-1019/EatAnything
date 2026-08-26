import { clearAccessToken, getAccessToken } from '@/auth/token'
import { env } from '@/config/env'
import { ApiClientError, type ApiErrorDetail, type ApiResponse } from './types'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
export type RequestHeaders = Record<string, string>

export interface RequestOptions<TData = unknown> {
  url: string
  method?: HttpMethod
  data?: TData
  headers?: RequestHeaders
  auth?: boolean
  skipAuthRefresh?: boolean
  timeout?: number
}

type RecordValue = Record<string, unknown>
type AuthRefreshHandler = (staleToken: string | null) => Promise<void>

let authRefreshHandler: AuthRefreshHandler | null = null
const DEFAULT_API_TIMEOUT = 15000
const DEFAULT_UPLOAD_TIMEOUT = 45000

export function setAuthRefreshHandler(handler: AuthRefreshHandler): void {
  authRefreshHandler = handler
}

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function camelCaseKey(value: string): string {
  return value.replace(/_([a-z0-9])/g, (_match, character: string) => character.toUpperCase())
}

function normalizeObjectKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(normalizeObjectKeys)
  if (!isRecord(value)) return value

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [camelCaseKey(key), normalizeObjectKeys(item)]),
  )
}

function normalizeResponseData(value: unknown): unknown {
  if (typeof value !== 'string') return normalizeObjectKeys(value)

  try {
    const parsed: unknown = JSON.parse(value)
    return normalizeObjectKeys(parsed)
  } catch {
    return value
  }
}

function joinUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.trim()
  if (!normalizedPath) {
    return baseUrl
  }
  return `${baseUrl}/${normalizedPath.replace(/^\/+/, '')}`
}

function parseErrorDetails(value: unknown): ApiErrorDetail[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.flatMap((item): ApiErrorDetail[] => {
    if (!isRecord(item) || typeof item.code !== 'string' || typeof item.message !== 'string') {
      return []
    }

    return [{
      code: item.code,
      message: item.message,
      row: typeof item.row === 'number' || item.row === null ? item.row : undefined,
      field: typeof item.field === 'string' || item.field === null ? item.field : undefined,
    }]
  })
}

function toApiClientError(payload: unknown, httpStatus: number): ApiClientError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const error = payload.error
    const status = typeof error.status === 'number' ? error.status : httpStatus
    const code = typeof error.code === 'string' ? error.code : `HTTP_${httpStatus}`
    const message = typeof error.message === 'string' ? error.message : `Request failed with status ${httpStatus}`

    return new ApiClientError(message, {
      status,
      code,
      field: typeof error.field === 'string' || error.field === null ? error.field : undefined,
      details: parseErrorDetails(error.details),
      requestId: typeof payload.requestId === 'string' ? payload.requestId : undefined,
    })
  }

  return new ApiClientError(`Request failed with status ${httpStatus}`, {
    status: httpStatus,
    code: `HTTP_${httpStatus}`,
  })
}

function unwrapApiResponse<T>(payload: unknown, httpStatus: number): T {
  if (!isRecord(payload) || !('data' in payload) || typeof payload.requestId !== 'string') {
    throw new ApiClientError('The server returned an invalid API response', {
      status: httpStatus,
      code: 'INVALID_API_RESPONSE',
    })
  }

  return (payload as unknown as ApiResponse<T>).data
}

interface TransportResult {
  data: unknown
  statusCode: number
}

interface UniRequestFailure {
  errMsg?: string
}

function networkError(failure: UniRequestFailure, fallback: string): ApiClientError {
  const message = failure.errMsg || fallback
  const isTimeout = /timeout|timed out|超时/i.test(message)
  const isRequestFailure = /request:fail/i.test(message)
  const displayMessage = isTimeout
    ? '服务器响应超时，请稍后重试'
    : isRequestFailure
      ? '无法连接服务器，请检查接口地址和小程序合法域名配置'
      : message
  return new ApiClientError(displayMessage, {
    code: isTimeout ? 'NETWORK_TIMEOUT' : isRequestFailure ? 'NETWORK_REQUEST_FAILED' : 'NETWORK_ERROR',
    cause: failure,
  })
}

export interface UploadOptions {
  url: string
  filePath: string
  name?: string
  formData?: Record<string, string>
  timeout?: number
  headers?: RequestHeaders
  auth?: boolean
  skipAuthRefresh?: boolean
}

function sendRequest<TData>(options: RequestOptions<TData>, token: string | null): Promise<TransportResult> {
  const headers: RequestHeaders = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (options.auth !== false && token) {
    headers.Authorization = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: joinUrl(env.apiBaseUrl, options.url),
      method: options.method as unknown as UniNamespace.RequestOptions['method'] ?? 'GET',
      data: options.data as UniNamespace.RequestOptions['data'],
      header: headers,
      timeout: options.timeout ?? DEFAULT_API_TIMEOUT,
      dataType: 'json',
      success: (response) => resolve({
        data: normalizeResponseData(response.data),
        statusCode: response.statusCode,
      }),
      fail: (failure: UniRequestFailure) => reject(networkError(failure, 'Unable to reach the server')),
    })
  })
}

async function executeRequest<T, TData>(options: RequestOptions<TData>, retryCount: number): Promise<T> {
  const tokenUsed = options.auth === false ? null : getAccessToken()
  const response = await sendRequest(options, tokenUsed)

  if (response.statusCode >= 200 && response.statusCode < 300) {
    if (response.statusCode === 204) return undefined as T
    return unwrapApiResponse<T>(response.data, response.statusCode)
  }

  const canRefreshAuth = response.statusCode === 401
    && options.auth !== false
    && options.skipAuthRefresh !== true
    && retryCount === 0

  if (canRefreshAuth) {
    if (!authRefreshHandler) {
      clearAccessToken()
      throw new ApiClientError('Authentication refresh is not configured', {
        status: 401,
        code: 'AUTH_REFRESH_UNAVAILABLE',
      })
    }
    await authRefreshHandler(tokenUsed)
    return executeRequest<T, TData>(options, retryCount + 1)
  }

  if (response.statusCode === 401 && options.auth !== false) {
    const currentToken = getAccessToken()
    if (!currentToken || currentToken === tokenUsed) {
      clearAccessToken()
    }
  }

  throw toApiClientError(response.data, response.statusCode)
}

export function request<T, TData = unknown>(options: RequestOptions<TData>): Promise<T> {
  return executeRequest<T, TData>(options, 0)
}

type RequestOverrides<TData> = Omit<RequestOptions<TData>, 'url' | 'method' | 'data'>

export function get<T, TQuery = undefined>(
  url: string,
  query?: TQuery,
  options: RequestOverrides<TQuery> = {},
): Promise<T> {
  return request<T, TQuery>({ ...options, url, method: 'GET', data: query })
}

export function post<T, TData = unknown>(url: string, data?: TData, options: RequestOverrides<TData> = {}): Promise<T> {
  return request<T, TData>({ ...options, url, method: 'POST', data })
}

export function patch<T, TData = unknown>(url: string, data?: TData, options: RequestOverrides<TData> = {}): Promise<T> {
  return request<T, TData>({ ...options, url, method: 'PATCH', data })
}

export function put<T, TData = unknown>(url: string, data?: TData, options: RequestOverrides<TData> = {}): Promise<T> {
  return request<T, TData>({ ...options, url, method: 'PUT', data })
}

export function del<T>(url: string, options: RequestOverrides<never> = {}): Promise<T> {
  return request<T>({ ...options, url, method: 'DELETE' })
}

interface UploadTransportResult {
  data: unknown
  statusCode: number
}

function sendUpload(options: UploadOptions, token: string | null): Promise<UploadTransportResult> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: joinUrl(env.apiBaseUrl, options.url),
      filePath: options.filePath,
      name: options.name ?? 'file',
      formData: options.formData,
      header: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers ?? {}) },
      timeout: options.timeout ?? DEFAULT_UPLOAD_TIMEOUT,
      success: (response) => resolve({
        data: normalizeResponseData(response.data),
        statusCode: response.statusCode,
      }),
      fail: (failure: UniRequestFailure) => reject(networkError(failure, 'Unable to upload the file')),
    })
  })
}

async function executeUpload<T>(options: UploadOptions, retryCount: number): Promise<T> {
  const tokenUsed = options.auth === false ? null : getAccessToken()
  const response = await sendUpload(options, tokenUsed)
  if (response.statusCode >= 200 && response.statusCode < 300) {
    if (response.statusCode === 204) return undefined as T
    return unwrapApiResponse<T>(response.data, response.statusCode)
  }

  if (response.statusCode === 401 && retryCount === 0 && options.auth !== false && options.skipAuthRefresh !== true) {
    if (!authRefreshHandler) {
      clearAccessToken()
      throw new ApiClientError('Authentication refresh is not configured', {
        status: 401,
        code: 'AUTH_REFRESH_UNAVAILABLE',
      })
    }
    await authRefreshHandler(tokenUsed)
    return executeUpload<T>(options, retryCount + 1)
  }

  if (response.statusCode === 401) {
    const currentToken = getAccessToken()
    if (!currentToken || currentToken === tokenUsed) clearAccessToken()
  }
  throw toApiClientError(response.data, response.statusCode)
}

export function uploadFile<T>(url: string, filePath: string, formData?: Record<string, string>, headers?: RequestHeaders, options: Pick<UploadOptions, 'auth' | 'skipAuthRefresh'> = {}): Promise<T> {
  return executeUpload<T>({ url, filePath, formData, headers, ...options }, 0)
}
