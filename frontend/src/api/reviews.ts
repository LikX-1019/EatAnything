import { del, get, put } from './client'
import type { PageData } from './stores'

export interface Reviewer {
  displayName: string
  avatarUrl?: string | null
}

export interface StoreReview {
  id: string
  storeId: string
  checkInId?: string | null
  rating: number
  content: string
  reviewer: Reviewer
  createdAt: string
  updatedAt: string
}

export interface ReviewStoreSnapshot {
  id: string
  storeCode: string
  name: string
  category: string
  address: string
  area: string
  imageUrl?: string | null
  isAvailable: boolean
}

export interface MyReview {
  id: string
  store: ReviewStoreSnapshot
  checkInId?: string | null
  rating: number
  content: string
  createdAt: string
  updatedAt: string
}

export interface ReviewUpsertRequest {
  rating: number
  content: string
}

interface ReviewQuery {
  page: number
  page_size: number
}

export function getStoreReviews(storeId: string, page = 1, pageSize = 20): Promise<PageData<StoreReview>> {
  return get<PageData<StoreReview>, ReviewQuery>(`/stores/${encodeURIComponent(storeId)}/reviews`, {
    page,
    page_size: pageSize,
  })
}

export async function getAllStoreReviews(storeId: string, pageSize = 100): Promise<PageData<StoreReview>> {
  const first = await getStoreReviews(storeId, 1, pageSize)
  const items = [...first.items]
  for (let page = 2; items.length < first.total; page += 1) {
    const next = await getStoreReviews(storeId, page, pageSize)
    if (!next.items.length) break
    items.push(...next.items)
  }
  return { ...first, items }
}

export function getMyReviews(page = 1, pageSize = 100): Promise<PageData<MyReview>> {
  return get<PageData<MyReview>, ReviewQuery>('/me/reviews', { page, page_size: pageSize })
}

export async function getAllMyReviews(pageSize = 100): Promise<PageData<MyReview>> {
  const first = await getMyReviews(1, pageSize)
  const items = [...first.items]
  for (let page = 2; items.length < first.total; page += 1) {
    const next = await getMyReviews(page, pageSize)
    if (!next.items.length) break
    items.push(...next.items)
  }
  return { ...first, items }
}

export function saveMyReview(storeId: string, payload: ReviewUpsertRequest): Promise<MyReview> {
  return put<MyReview, ReviewUpsertRequest>(`/me/reviews/${encodeURIComponent(storeId)}`, payload)
}

export function deleteMyReview(storeId: string): Promise<void> {
  return del<void>(`/me/reviews/${encodeURIComponent(storeId)}`)
}
