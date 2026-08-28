import { get, post, put, uploadFile } from './client'

export interface SchoolSummary {
  id: string
  schoolCode: string
  name: string
  city?: string | null
  district?: string | null
  address?: string | null
}

export interface UserStats {
  favoriteCount: number
  eatenCount: number
  checkinCount: number
  reviewCount: number
  historyCount: number
}

export interface UserProfile {
  id: string
  nickname: string
  avatarUrl?: string | null
  schoolId?: string | null
  school?: SchoolSummary | null
  slogan?: string | null
  gender?: 'male' | 'female' | 'other' | 'secret' | null
  birthday?: string | null
  level: number
  stats: UserStats
  createdAt: string
}

export interface SchoolWeatherData {
  schoolId: string
  forecastDate: string
  temperatureMin: number
  temperatureMax: number
  weatherCode: string
  weatherText: string
  icon: string
  updatedAt: string
  source: 'open_meteo' | 'qweather'
}

export interface ProfileUpdate {
  nickname?: string
  slogan?: string | null
  gender?: 'male' | 'female' | 'other' | 'secret' | null
  birthday?: string | null
}

export function getCurrentUser(): Promise<UserProfile> {
  return get<UserProfile>('/me')
}

export function getSchools(): Promise<SchoolSummary[]> {
  return get<SchoolSummary[]>('/schools')
}

export function selectUserSchool(schoolId: string): Promise<UserProfile> {
  return put<UserProfile>(`/me/school/${encodeURIComponent(schoolId)}`)
}

export function getCurrentSchoolWeather(): Promise<SchoolWeatherData> {
  return get<SchoolWeatherData>('/me/weather')
}

export function updateProfile(payload: ProfileUpdate): Promise<UserProfile> {
  return put<UserProfile>('/me/profile', payload)
}

// #ifdef MP-WEIXIN
function readFileAsBase64(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.getFileSystemManager().readFile({
      filePath,
      encoding: 'base64',
      success: (result) => resolve(String(result.data)),
      fail: (failure) => reject(new Error(failure.errMsg || '读取图片失败')),
    })
  })
}
// #endif

export async function uploadAvatar(filePath: string): Promise<{ avatarUrl: string }> {
  // 微信端使用 JSON base64 上传，只依赖 request 合法域名，不依赖 uploadFile 域名。
  // #ifdef MP-WEIXIN
  const dataBase64 = await readFileAsBase64(filePath)
  return post<{ avatarUrl: string }>('/me/avatar/data', { dataBase64, contentType: 'image/jpeg' })
  // #endif
  return uploadFile<{ avatarUrl: string }>('/me/avatar', filePath)
}
