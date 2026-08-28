import { getAccessToken } from '../auth/token'
import { env } from '../config/env'

declare const wx: { env: { USER_DATA_PATH: string } }

const localCache = new Map<string, string>()

function localFilePath(source: string): string {
  let hash = 2166136261
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return `${wx.env.USER_DATA_PATH}/avatar-${(hash >>> 0).toString(16)}.png`
}

export function resolveAvatarSource(source: string | null | undefined): Promise<string> {
  if (!source) return Promise.resolve('')
  if (!source.startsWith('/api/v1')) return Promise.resolve(source)

  const absolute = `${env.apiBaseUrl}${source.slice('/api/v1'.length)}`
  // #ifdef MP-WEIXIN
  const cached = localCache.get(absolute)
  if (cached) return Promise.resolve(cached)

  return new Promise((resolve, reject) => {
    const token = getAccessToken()
    uni.request({
      url: absolute,
      method: 'GET',
      timeout: 15000,
      responseType: 'arraybuffer',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (response) => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`头像加载失败：HTTP ${response.statusCode}`))
          return
        }
        const data = response.data as ArrayBuffer
        uni.getFileSystemManager().writeFile({
          filePath: localFilePath(absolute),
          data,
          success: () => {
            localCache.set(absolute, localFilePath(absolute))
            resolve(localFilePath(absolute))
          },
          fail: (failure) => reject(new Error(failure.errMsg || '头像写入本地失败')),
        })
      },
      fail: (failure) => reject(new Error(failure.errMsg || '头像请求失败')),
    })
  })
  // #endif
}
