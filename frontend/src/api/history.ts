import { get } from './client'
import type { PageData } from './stores'

export interface HistoryStoreSnapshot {
  id: string
  storeCode: string
  name: string
  category: string
  address: string
  area: string
  imageUrl?: string | null
  isAvailable: boolean
}

export interface HistoryRecord {
  id: string
  action: 'RANDOM_PICK' | 'DETAIL_VIEW' | string
  occurredAt: string
  store: HistoryStoreSnapshot
}

interface HistoryQuery {
  action?: string
  page: number
  page_size: number
}

export function getHistory(page = 1, pageSize = 100): Promise<PageData<HistoryRecord>> {
  return get<PageData<HistoryRecord>, HistoryQuery>('/me/history', { page, page_size: pageSize })
}
