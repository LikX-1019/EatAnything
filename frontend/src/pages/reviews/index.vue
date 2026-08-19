<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { ApiClientError } from '../../api/types'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'
const appStore = useAppStore()
onShow(async () => {
  try { await appStore.initialize() }
  catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '店铺数据加载失败', icon: 'none' }) }
})
function writeReview() { uni.navigateTo({ url: '/pages/reviews/create' }) }
</script>

<template>
  <view class="page-shell reviews-page" :class="appStore.fontClass"><PageHeader title="我的评价" back /><view class="page-pad"><view v-if="appStore.reviews.length" class="review-list"><view v-for="review in appStore.reviews" :key="review.id" class="review-item"><view class="review-head"><view><text class="review-name">{{ appStore.findStore(review.storeId)?.name }}</text><text class="review-area">{{ appStore.findArea(appStore.findStore(review.storeId))?.name }}</text></view><text class="review-date">{{ review.date }}</text></view><text class="stars">★{{ review.rating }} <text class="stars-total">/ 5</text></text><text class="review-copy">{{ review.content }}</text></view></view><EmptyState v-else title="还没有评价" description="吃完一家店后，记录真实感受" /><button class="write-button" @tap="writeReview">写一条评价</button></view></view>
</template>

<style scoped>
.reviews-page { background: var(--page); }
.page-pad { padding: 28rpx 30rpx; }
.review-list { display: flex; flex-direction: column; gap: 16rpx; }
.review-item { padding: 24rpx; border-radius: 14rpx; background: #fff; }
.review-head { display: flex; justify-content: space-between; gap: 16rpx; }
.review-name { display: block; font-size: 29rpx; font-weight: 800; }
.review-area { display: block; margin-top: 6rpx; color: var(--muted); font-size: 22rpx; }
.review-date { color: var(--muted); font-size: 21rpx; }
.stars { display: block; margin-top: 16rpx; color: var(--amber); font-size: 27rpx; font-weight: 800; }
.stars-total { color: #a0afa7; font-size: 22rpx; font-weight: 400; }
.review-copy { display: block; margin-top: 12rpx; color: #52665c; font-size: 25rpx; line-height: 1.6; }
.write-button { width: 100%; height: 82rpx; margin-top: 24rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; font-weight: 800; }
</style>
