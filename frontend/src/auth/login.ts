import { devLogin, type AuthData, wechatLogin } from '@/api/auth'
import { ApiClientError } from '@/api/types'
import { env } from '@/config/env'
import { clearAccessToken, getAccessToken } from './token'

let loginPromise: Promise<AuthData> | null = null

interface UniLoginFailure {
  errMsg?: string
}

function getWechatLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.login({
      provider: 'weixin',
      success: (result) => {
        if (result.code) {
          resolve(result.code)
          return
        }

        reject(new ApiClientError('WeChat login did not return a code', {
          code: 'WECHAT_LOGIN_CODE_MISSING',
        }))
      },
      fail: (failure: UniLoginFailure) => reject(new ApiClientError(
        failure.errMsg || 'Unable to start WeChat login',
        { code: 'WECHAT_LOGIN_FAILED', cause: failure },
      )),
    })
  })
}

async function loginWithWechat(): Promise<AuthData> {
  return wechatLogin(await getWechatLoginCode())
}

async function performLogin(): Promise<AuthData> {
  // #ifdef MP-WEIXIN
  return loginWithWechat()
  // #endif

  // #ifndef MP-WEIXIN
  if (env.devLoginEnabled) {
    return devLogin(env.devUserId)
  }

  throw new ApiClientError('No login method is available on this platform', {
    code: 'LOGIN_UNAVAILABLE',
  })
  // #endif
}

export function login(): Promise<AuthData> {
  if (!loginPromise) {
    loginPromise = performLogin().finally(() => {
      loginPromise = null
    })
  }

  return loginPromise
}

export async function ensureLogin(): Promise<void> {
  if (getAccessToken()) {
    return
  }
  await login()
}

export async function forceRelogin(staleToken?: string | null): Promise<void> {
  const currentToken = getAccessToken()

  // A different concurrent request may already have refreshed the stale token.
  if (staleToken !== undefined && currentToken && currentToken !== staleToken) {
    return
  }

  clearAccessToken()
  await login()
}
