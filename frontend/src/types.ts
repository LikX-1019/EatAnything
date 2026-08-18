export interface CampusArea {
  id: string
  name: string
}

export interface SchoolItem {
  id: string
  name: string
  areas: CampusArea[]
}

export interface StoreItem {
  id: number
  schoolId: string
  areaId: string
  name: string
  category: string
  address: string
  image: string
  eaten: boolean
  favorite: boolean
  score: number
}

export interface ReviewItem {
  id: number
  storeId: number
  rating: number
  content: string
  date: string
}

export type HistoryAction = '随机抽取' | '浏览店铺' | '锁定选择' | '到店打卡' | '加入收藏' | '提交评价'

export interface HistoryItem {
  id: number
  storeId: number
  action: HistoryAction
  date: string
}

export interface FeedComment {
  id: number
  storeId: number
  user: string
  content: string
  time: string
}
