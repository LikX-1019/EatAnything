export const ADMIN_ACCESS_TOKEN_STORAGE_KEY = 'eat_anything_admin_access_token'

export function getAdminAccessToken(): string | null {
  const value: unknown = uni.getStorageSync(ADMIN_ACCESS_TOKEN_STORAGE_KEY)
  return typeof value === 'string' && value.trim() ? value : null
}

export function setAdminAccessToken(token: string): void {
  if (!token.trim()) throw new TypeError('Admin access token cannot be empty')
  uni.setStorageSync(ADMIN_ACCESS_TOKEN_STORAGE_KEY, token.trim())
}

export function clearAdminAccessToken(): void {
  uni.removeStorageSync(ADMIN_ACCESS_TOKEN_STORAGE_KEY)
}
