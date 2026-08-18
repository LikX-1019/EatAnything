import { setAccessToken } from '@/auth/token'
import { env } from '@/config/env'
import { ApiClientError } from './types'
import { post } from './client'

export interface UserSummary {
  id: string
  nickname: string
  avatarUrl?: string | null
}

export interface AuthData {
  accessToken: string
  tokenType: string
  expiresIn: number
  user: UserSummary
}

function saveLogin(authData: AuthData): AuthData {
  setAccessToken(authData.accessToken)
  return authData
}

export async function wechatLogin(code: string): Promise<AuthData> {
  const authData = await post<AuthData, { code: string }>(
    '/auth/wechat-login',
    { code },
    { auth: false, skipAuthRefresh: true },
  )
  return saveLogin(authData)
}

export async function devLogin(externalId: string = env.devUserId): Promise<AuthData> {
  if (env.isProduction || !env.devLoginEnabled) {
    throw new ApiClientError('Development login is disabled in this environment', {
      code: 'DEV_LOGIN_DISABLED',
    })
  }

  const authData = await post<AuthData, { externalId: string }>(
    '/auth/dev-login',
    { externalId },
    { auth: false, skipAuthRefresh: true },
  )
  return saveLogin(authData)
}
