import type { StoreSummary } from './api/stores'

export type StoreItem = StoreSummary

export interface StoreArea {
  id: string
  name: string
}

export interface FeedComment {
  id: number
  storeId: string | number
  user: string
  content: string
  time: string
}
