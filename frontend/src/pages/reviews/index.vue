<script setup lang="ts">
import { ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { deleteMyReview, getAllMyReviews, type MyReview } from '../../api/reviews'
import { ApiClientError } from '../../api/types'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import FallbackImage from '../../components/FallbackImage.vue'
import { useAppStore } from '../../stores/useAppStore'
import { useUserStore } from '../../stores/useUserStore'
import { storeImageUrl } from '../../utils/store'

const appStore = useAppStore()
const userStore = useUserStore()
const reviews = ref<MyReview[]>([])
const loading = ref(true)
const errorMessage = ref('')

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : `${date.getMonth() + 1}月${date.getDate()}日`
}

async function loadReviews() {
  loading.value = true
  errorMessage.value = ''
  try {
    await appStore.initialize()
    reviews.value = (await getAllMyReviews()).items
  } catch (cause) {
    errorMessage.value = cause instanceof ApiClientError ? cause.message : '评价加载失败，请重试'
    uni.showToast({ title: cause instanceof ApiClientError ? cause.message : '评价加载失败', icon: 'none' })
  } finally {
    loading.value = false
    if (refreshing) uni.stopPullDownRefresh()
  }
}

function writeReview() { uni.navigateTo({ url: '/pages/reviews/create' }) }
function editReview(review: MyReview) {
  uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(review.store.id)}` })
}

function manageReview(review: MyReview) {
  uni.showActionSheet({
    itemList: ['修改评价', '删除评价'],
    success: async ({ tapIndex }) => {
      if (tapIndex === 0) {
        editReview(review)
        return
      }
      if (tapIndex !== 1) return
      try {
        await deleteMyReview(review.store.id)
        reviews.value = reviews.value.filter((item) => item.id !== review.id)
        await Promise.all([userStore.refreshProfile().catch(() => undefined), appStore.refreshStore(review.store.id).catch(() => undefined)])
        uni.showToast({ title: '评价已删除', icon: 'success' })
      } catch (cause) {
        uni.showToast({ title: cause instanceof ApiClientError ? cause.message : '删除评价失败', icon: 'none' })
      }
    },
  })
}

let refreshing = false
onShow(() => { void loadReviews() })
onPullDownRefresh(() => { refreshing = true; void loadReviews().finally(() => { refreshing = false }) })
</script>

<template>
  <view class="page-shell reviews-page" :class="appStore.fontClass"><PageHeader title="我的评价" back /><view class="page-pad"><view v-if="loading" class="loading-copy">正在加载评价…</view><view v-else-if="errorMessage" class="loading-copy"><text>{{ errorMessage }}</text><button class="retry-button" @tap="loadReviews()">重新加载</button></view><view v-else-if="reviews.length" class="review-list"><view v-for="review in reviews" :key="review.id" class="review-item" @tap="manageReview(review)"><view class="review-head"><view class="store-head"><FallbackImage class="store-review-image" :src="storeImageUrl(review.store)" /><view><text class="review-name">{{ review.store.name }}</text><text class="review-area">{{ review.store.area || '未分区' }}</text></view></view><text class="review-date">{{ formatDate(review.updatedAt) }}</text></view><text class="stars">{{ '★'.repeat(review.rating) }}<text class="stars-off">{{ '★'.repeat(5 - review.rating) }}</text></text><text class="review-copy">{{ review.content }}</text></view></view><EmptyState v-else title="你还没有发表评价" description="完成打卡后，记录真实感受" /><button class="write-button" @tap="writeReview">写一条评价</button></view></view>
</template>

<style scoped>
.reviews-page { background: var(--page); }.page-pad { padding: 28rpx 30rpx; }.loading-copy { padding: 80rpx 0; color: var(--muted); text-align: center; }.retry-button { display: block; margin: 22rpx auto 0; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }.review-list { display: flex; flex-direction: column; gap: 16rpx; }.review-item { padding: 24rpx; border-radius: 14rpx; background: #fff; }.review-head { display: flex; justify-content: space-between; gap: 16rpx; }.store-head { display: flex; align-items: center; min-width: 0; gap: 13rpx; }.store-review-image { width: 70rpx; height: 70rpx; border-radius: 10rpx; }.review-name { display: block; font-size: 29rpx; font-weight: 800; }.review-area { display: block; margin-top: 6rpx; color: var(--muted); font-size: 22rpx; }.review-date { color: var(--muted); font-size: 21rpx; }.stars { display: block; margin-top: 16rpx; color: var(--amber); font-size: 27rpx; letter-spacing: 2rpx; }.stars-off { color: #d8ddd6; }.review-copy { display: block; margin-top: 12rpx; color: #52665c; font-size: 25rpx; line-height: 1.6; }.write-button { width: 100%; height: 82rpx; margin-top: 24rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; }
</style>
