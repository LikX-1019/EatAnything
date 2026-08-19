import { get, post } from './client'

export interface PageData<T> {
  items: T[]
  page: number
  pageSize: number
  total: number
}

export interface StoreSummary {
  id: string
  storeCode: string
  schoolId?: string | null
  schoolCode?: string | null
  schoolName?: string | null
  name: string
  category: string
  address: string
  area: string
  imageUrl?: string | null
  score?: number | null
  reviewCount: number
  isFavorite: boolean
  isEaten: boolean
}

export interface GetStoresParams {
  keyword?: string
  page?: number
  pageSize?: number
}

interface StoreQuery {
  keyword?: string
  page: number
  page_size: number
}

export interface RandomStoreData {
  store: StoreSummary
  historyId: string
}

export function getStores(params: GetStoresParams = {}): Promise<PageData<StoreSummary>> {
  const keyword = params.keyword?.trim()
  const query: StoreQuery = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 100,
  }
  if (keyword) query.keyword = keyword
  return get<PageData<StoreSummary>, StoreQuery>('/stores', query)
}

export function searchStores(keyword: string, page = 1, pageSize = 20): Promise<PageData<StoreSummary>> {
  return getStores({ keyword, page, pageSize })
}

export function randomStore(excludeStoreId?: string): Promise<RandomStoreData> {
  return post<RandomStoreData, { excludeStoreId?: string }>(
    '/stores/random',
    excludeStoreId ? { excludeStoreId } : {},
  )
}
