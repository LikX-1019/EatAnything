import { del, get, put } from './client'
import type { PageData, StoreSummary } from './stores'

export interface StateQuery {
  keyword?: string
  page?: number
  pageSize?: number
}

interface StateQueryPayload {
  keyword?: string
  page: number
  page_size: number
}

export interface FavoriteState {
  storeId: string
  isFavorite: boolean
}

function queryPayload(params: StateQuery = {}): StateQueryPayload {
  const query: StateQueryPayload = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 100,
  }
  const keyword = params.keyword?.trim()
  if (keyword) query.keyword = keyword
  return query
}

export function getFavorites(params?: StateQuery): Promise<PageData<StoreSummary>> {
  return get<PageData<StoreSummary>, StateQueryPayload>('/me/favorites', queryPayload(params))
}

export function addFavorite(storeId: string): Promise<FavoriteState> {
  return put<FavoriteState>(`/me/favorites/${encodeURIComponent(storeId)}`)
}

export function removeFavorite(storeId: string): Promise<FavoriteState> {
  return del<FavoriteState>(`/me/favorites/${encodeURIComponent(storeId)}`)
}

export function getEaten(params?: StateQuery): Promise<PageData<StoreSummary>> {
  return get<PageData<StoreSummary>, StateQueryPayload>('/me/eaten', queryPayload(params))
}
