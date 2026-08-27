<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { getAllStoreReviews, type StoreReview } from '../../api/reviews'
import { ApiClientError } from '../../api/types'
import type { StoreDetail } from '../../api/stores'
import EmptyState from '../../components/EmptyState.vue'
import FallbackImage from '../../components/FallbackImage.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'
import { storeImageUrl, storeScoreLabel } from '../../utils/store'

const appStore = useAppStore()
const storeId = ref('')
const detail = ref<StoreDetail | null>(null)
const reviews = ref<StoreReview[]>([])
const reviewTotal = ref(0)
const loading = ref(true)
const errorMessage = ref('')
const favoriteLoading = ref(false)
const isEaten = computed(() => detail.value?.isEaten ?? false)

onLoad((query) => {
  storeId.value = typeof query?.storeId === 'string' ? query.storeId : ''
})

async function load() {
  if (!storeId.value) {
    errorMessage.value = '店铺参数无效'
    loading.value = false
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    await appStore.initialize()
    const [nextDetail, reviewPage] = await Promise.all([
      appStore.refreshStore(storeId.value),
      getAllStoreReviews(storeId.value),
    ])
    detail.value = nextDetail
    reviews.value = reviewPage.items
    reviewTotal.value = reviewPage.total
  } catch (cause) {
    errorMessage.value = cause instanceof ApiClientError ? cause.message : '店铺详情加载失败'
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!detail.value || favoriteLoading.value) return
  favoriteLoading.value = true
  try {
    detail.value.isFavorite = await appStore.toggleFavorite(detail.value.id)
    uni.showToast({ title: detail.value.isFavorite ? '已加入收藏' : '已取消收藏', icon: 'none' })
  } catch (cause) {
    uni.showToast({ title: cause instanceof ApiClientError ? cause.message : '收藏操作失败', icon: 'none' })
  } finally {
    favoriteLoading.value = false
  }
}

function writeReview() {
  if (!detail.value) return
  if (!detail.value.isEaten) {
    uni.showToast({ title: '完成打卡后才能评价', icon: 'none' })
    return
  }
  uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(detail.value.id)}` })
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : `${date.getMonth() + 1}月${date.getDate()}日`
}

onShow(() => { if (storeId.value) void load() })
onPullDownRefresh(() => { void load().finally(() => uni.stopPullDownRefresh()) })
</script>

<template>
  <view class="page-shell detail-page" :class="appStore.fontClass">
    <PageHeader title="店铺详情" back />
    <view v-if="loading" class="state-copy">正在加载店铺信息…</view>
    <view v-else-if="errorMessage" class="state-copy"><text>{{ errorMessage }}</text><button class="retry-button" @tap="load">重新加载</button></view>
    <view v-else-if="detail" class="page-pad">
      <FallbackImage class="hero-image" :src="storeImageUrl(detail)" />
      <view class="title-row"><view class="title-copy"><text class="store-name">{{ detail.name }}</text><text class="category">{{ detail.category || '校园餐饮' }} · {{ detail.area || '未分区' }}</text></view><text class="score">★ {{ storeScoreLabel(detail) }}</text></view>
      <text class="address">{{ [detail.city, detail.district, detail.address].filter(Boolean).join(' · ') }}</text>
      <text v-if="detail.description" class="description">{{ detail.description }}</text>
      <view class="state-row"><text>{{ detail.reviewCount }} 条评价</text><text>{{ isEaten ? '已吃过' : '还未打卡' }}</text><button class="favorite-button" :disabled="favoriteLoading" @tap="toggleFavorite">{{ detail.isFavorite ? '♥ 已收藏' : '♡ 收藏' }}</button></view>
      <view class="section-heading"><text>真实评价</text><text>{{ reviewTotal }} 条</text></view>
      <view v-if="reviews.length" class="review-list"><view v-for="review in reviews" :key="review.id" class="review-item"><view class="review-head"><view class="reviewer"><FallbackImage v-if="review.reviewer.avatarUrl" class="avatar" :src="review.reviewer.avatarUrl" /><view v-else class="avatar-fallback">{{ review.reviewer.displayName.slice(0, 1) }}</view><text>{{ review.reviewer.displayName }}</text></view><text class="review-date">{{ formatDate(review.createdAt) }}</text></view><text class="stars">{{ '★'.repeat(review.rating) }}<text class="stars-off">{{ '★'.repeat(5 - review.rating) }}</text></text><text class="review-content">{{ review.content }}</text></view></view>
      <EmptyState v-else title="还没有评价" description="完成打卡后，留下第一条真实感受吧" />
      <button class="write-button" @tap="writeReview">{{ isEaten ? '写评价' : '先去打卡再评价' }}</button>
    </view>
  </view>
</template>

<style scoped>
.detail-page { background: var(--page); }
.page-pad { padding: 22rpx 30rpx 50rpx; }
.state-copy { display: flex; align-items: center; justify-content: center; min-height: 560rpx; padding: 40rpx; color: var(--muted); font-size: 28rpx; flex-direction: column; }
.retry-button { margin-top: 22rpx; padding: 0 26rpx; height: 70rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 26rpx; }
.hero-image { width: 100%; height: 380rpx; border-radius: 14rpx 8rpx 16rpx 10rpx; background: #f2e8d5; box-shadow: var(--paper-shadow); }
.title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 20rpx; margin-top: 22rpx; }.title-copy { min-width: 0; flex: 1; }.store-name { display: block; font-size: 42rpx; font-weight: 900; }.category { display: block; margin-top: 9rpx; color: var(--muted); font-size: 25rpx; }.score { flex: 0 0 auto; color: var(--amber); font-size: 29rpx; font-weight: 900; }.address { display: block; margin-top: 16rpx; color: var(--muted); font-size: 25rpx; }.description { display: block; margin-top: 18rpx; color: #5f5144; font-size: 27rpx; line-height: 1.7; }
.state-row { display: flex; align-items: center; gap: 18rpx; margin-top: 22rpx; color: var(--muted); font-size: 23rpx; }.favorite-button { margin-left: auto; padding: 0 22rpx; height: 66rpx; border: 1rpx solid #dfa092; border-radius: 9rpx; background: #fffaf0; color: var(--brand); font-size: 24rpx; }.favorite-button[disabled] { opacity: .6; }
.section-heading { display: flex; justify-content: space-between; margin-top: 36rpx; padding-bottom: 13rpx; border-bottom: 1rpx solid var(--line); font-size: 31rpx; font-weight: 900; }.section-heading text:last-child { color: var(--muted); font-size: 22rpx; font-weight: 400; }
.review-list { display: flex; flex-direction: column; }.review-item { padding: 22rpx 0; border-bottom: 1rpx solid var(--line); }.review-head { display: flex; align-items: center; justify-content: space-between; }.reviewer { display: flex; align-items: center; gap: 12rpx; font-size: 25rpx; font-weight: 800; }.avatar, .avatar-fallback { display: flex; align-items: center; justify-content: center; width: 56rpx; height: 56rpx; border-radius: 50%; }.avatar-fallback { background: #efc19b; color: #79543c; }.avatar { background: #f4ead9; }.review-date { color: var(--muted); font-size: 21rpx; }.stars { display: block; margin-top: 13rpx; color: var(--amber); font-size: 25rpx; letter-spacing: 2rpx; }.stars-off { color: #d8ddd6; }.review-content { display: block; margin-top: 10rpx; color: #5b675f; font-size: 26rpx; line-height: 1.6; }.write-button { width: 100%; height: 80rpx; margin-top: 26rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 28rpx; font-weight: 800; }
</style>
