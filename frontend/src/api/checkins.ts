import { get } from './client'
import { uploadFile } from './upload'
import type { PageData } from './stores'

export interface CheckInItem {
  id: string
  storeId: string
  photoUrl: string
  note?: string | null
  checkedAt: string
  createdAt: string
}

export interface CheckInQueryParams {
  page?: number
  pageSize?: number
}

interface CheckInQuery {
  page: number
  page_size: number
}

export function createCheckIn(storeId: string, filePath: string, note?: string): Promise<CheckInItem> {
  const formData = note?.trim() ? { note: note.trim() } : undefined
  return uploadFile<CheckInItem>(`/stores/${encodeURIComponent(storeId)}/check-ins`, filePath, formData)
}

export function updateCheckIn(checkInId: string, filePath: string, note?: string): Promise<CheckInItem> {
  const formData = note?.trim() ? { note: note.trim() } : undefined
  return uploadFile<CheckInItem>(`/me/check-ins/${encodeURIComponent(checkInId)}`, filePath, formData)
}

export function getMyCheckIns(params: CheckInQueryParams = {}): Promise<PageData<CheckInItem>> {
  return get<PageData<CheckInItem>, CheckInQuery>('/me/check-ins', {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 100,
  })
}
