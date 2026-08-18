export const ACCESS_TOKEN_STORAGE_KEY = 'eat_anything_access_token'

export function getAccessToken(): string | null {
  const storedToken: unknown = uni.getStorageSync(ACCESS_TOKEN_STORAGE_KEY)
  return typeof storedToken === 'string' && storedToken.length > 0 ? storedToken : null
}

export function setAccessToken(token: string): void {
  const normalizedToken = token.trim()
  if (!normalizedToken) {
    throw new TypeError('Access token cannot be empty')
  }
  uni.setStorageSync(ACCESS_TOKEN_STORAGE_KEY, normalizedToken)
}

export function clearAccessToken(): void {
  uni.removeStorageSync(ACCESS_TOKEN_STORAGE_KEY)
}
