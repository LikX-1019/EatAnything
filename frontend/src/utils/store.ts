import type { StoreSummary } from '@/api/stores'

// 使用极小的内联占位图，避免把本地餐品图片打进小程序主包。
export const STORE_IMAGE_FALLBACK = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='

export function storeImageUrl(store: Pick<StoreSummary, 'imageUrl'> | { imageUrl?: string | null } | undefined | null): string {
  return store?.imageUrl || STORE_IMAGE_FALLBACK
}

export function storeScoreLabel(store: StoreSummary): string {
  return store.score === null || store.score === undefined ? '暂无评分' : store.score.toFixed(1)
}
