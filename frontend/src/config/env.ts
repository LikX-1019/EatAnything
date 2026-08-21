function requireApiBaseUrl(value: string | undefined): string {
  const apiBaseUrl = value?.trim().replace(/\/+$/, '')

  if (!apiBaseUrl) {
    throw new Error('VITE_API_BASE_URL is required')
  }

  if (!/^https?:\/\//i.test(apiBaseUrl)) {
    throw new Error('VITE_API_BASE_URL must be an absolute HTTP(S) URL')
  }

  return apiBaseUrl
}

function readBoolean(value: string | undefined, name: string): boolean {
  if (value === undefined || value.trim() === '') {
    return false
  }

  const normalized = value.trim().toLowerCase()
  if (normalized === 'true') {
    return true
  }
  if (normalized === 'false') {
    return false
  }

  throw new Error(`${name} must be either "true" or "false"`)
}

const mode = import.meta.env.MODE
const isProduction = mode === 'production'
const isDevelopment = mode === 'development'
const isTest = mode === 'test'
const devLoginRequested = readBoolean(import.meta.env.VITE_DEV_LOGIN_ENABLED, 'VITE_DEV_LOGIN_ENABLED')
const devUserId = import.meta.env.VITE_DEV_USER_ID?.trim() || 'demo-user'

export const env = Object.freeze({
  apiBaseUrl: requireApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
  mode,
  isDev: isDevelopment,
  isTest,
  isProduction,
  devLoginEnabled: !isProduction && (isDevelopment || isTest) && devLoginRequested,
  devUserId,
})
