const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
const TOKEN_KEY = 'eat_anything_admin_web_token'

export interface PageData<T> { items: T[]; page: number; pageSize: number; total: number }

function camelKey(value: string) { return value.replace(/_([a-z0-9])/g, (_, char: string) => char.toUpperCase()) }
function normalize(value: unknown): any {
  if (Array.isArray(value)) return value.map(normalize)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [camelKey(key), normalize(item)]))
  return value
}

export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setToken(value: string) { localStorage.setItem(TOKEN_KEY, value) }
export function clearToken() { localStorage.removeItem(TOKEN_KEY) }

export class ApiError extends Error {
  constructor(message: string, public status = 0, public code = 'REQUEST_FAILED') { super(message) }
}

function queryString(params?: Record<string, unknown>) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) query.set(key.replace(/[A-Z]/g, char => `_${char.toLowerCase()}`), String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export async function request<T>(path: string, options: RequestInit = {}, params?: Record<string, unknown>): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const res = await fetch(`${API_BASE}${path}${queryString(params)}`, { ...options, headers })
  if (res.status === 401) {
    clearToken()
    if (!location.pathname.endsWith('/login')) location.assign('/admin/login')
  }
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}))
    throw new ApiError(payload?.error?.message || `请求失败（${res.status}）`, res.status, payload?.error?.code)
  }
  if (res.status === 204) return undefined as T
  const payload = normalize(await res.json())
  return payload.data as T
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => request<T>(path, {}, params),
  post: <T>(path: string, data?: unknown) => request<T>(path, { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data ?? {}) }),
  patch: <T>(path: string, data: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: <T>(path: string, params?: Record<string, unknown>) => request<T>(path, { method: 'DELETE' }, params),
}

export async function authenticatedImage(path: string): Promise<string> {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path.startsWith('/api/') ? path : `${API_BASE}${path}`, { headers })
  if (!res.ok) throw new ApiError('照片加载失败', res.status)
  return URL.createObjectURL(await res.blob())
}
