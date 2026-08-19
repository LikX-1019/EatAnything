import { get, put } from './client'

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
  level: number
  stats: UserStats
  createdAt: string
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
