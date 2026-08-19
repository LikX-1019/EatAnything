import type { StoreSummary } from '@/api/stores'

export const STORE_IMAGE_FALLBACK = '/static/images/foods/rice-bowl.jpg'

export function storeImageUrl(store: StoreSummary | undefined | null): string {
  return store?.imageUrl || STORE_IMAGE_FALLBACK
}

export function storeScoreLabel(store: StoreSummary): string {
  return store.score === null || store.score === undefined ? '暂无评分' : store.score.toFixed(1)
}
