import { forceRelogin } from '@/auth/login'
import { clearAccessToken, getAccessToken } from '@/auth/token'
import { env } from '@/config/env'
import { ApiClientError, type ApiErrorDetail, type ApiResponse } from './types'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
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

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function normalizeResponseData(value: unknown): unknown {
  if (typeof value !== 'string') {
    return value
  }

  try {
    const parsed: unknown = JSON.parse(value)
    return parsed
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
      method: options.method ?? 'GET',
      data: options.data as UniNamespace.RequestOptions['data'],
      header: headers,
      timeout: options.timeout,
      dataType: 'json',
      success: (response) => resolve({
        data: normalizeResponseData(response.data),
        statusCode: response.statusCode,
      }),
      fail: (failure: UniRequestFailure) => reject(new ApiClientError(
        failure.errMsg || 'Unable to reach the server',
        { code: 'NETWORK_ERROR', cause: failure },
      )),
    })
  })
}

async function executeRequest<T, TData>(options: RequestOptions<TData>, retryCount: number): Promise<T> {
  const tokenUsed = options.auth === false ? null : getAccessToken()
  const response = await sendRequest(options, tokenUsed)

  if (response.statusCode >= 200 && response.statusCode < 300) {
    return unwrapApiResponse<T>(response.data, response.statusCode)
  }

  const canRefreshAuth = response.statusCode === 401
    && options.auth !== false
    && options.skipAuthRefresh !== true
    && retryCount === 0

  if (canRefreshAuth) {
    await forceRelogin(tokenUsed)
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

export function get<T>(url: string, options: RequestOverrides<never> = {}): Promise<T> {
  return request<T>({ ...options, url, method: 'GET' })
}

export function post<T, TData = unknown>(url: string, data?: TData, options: RequestOverrides<TData> = {}): Promise<T> {
  return request<T, TData>({ ...options, url, method: 'POST', data })
}

export function put<T, TData = unknown>(url: string, data?: TData, options: RequestOverrides<TData> = {}): Promise<T> {
  return request<T, TData>({ ...options, url, method: 'PUT', data })
}

export function del<T>(url: string, options: RequestOverrides<never> = {}): Promise<T> {
  return request<T>({ ...options, url, method: 'DELETE' })
}
