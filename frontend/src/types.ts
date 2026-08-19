import type { StoreSummary } from './api/stores'

export type StoreItem = StoreSummary

export interface StoreArea {
  id: string
  name: string
}

export interface ReviewItem {
  id: number
  storeId: string | number
  rating: number
  content: string
  date: string
}

export type HistoryAction = '随机抽取' | '浏览店铺' | '锁定选择' | '到店打卡' | '加入收藏' | '提交评价'

export interface HistoryItem {
  id: number
  storeId: string | number
  action: HistoryAction
  date: string
}

export interface FeedComment {
  id: number
  storeId: string | number
  user: string
  content: string
  time: string
}
