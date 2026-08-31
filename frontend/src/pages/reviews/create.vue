<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { getAllMyReviews, saveMyReview } from '../../api/reviews'
import { ApiClientError } from '../../api/types'
import { useAppStore } from '../../stores/useAppStore'
import { useUserStore } from '../../stores/useUserStore'
import PageHeader from '../../components/PageHeader.vue'
import FallbackImage from '../../components/FallbackImage.vue'
import EmptyState from '../../components/EmptyState.vue'
import { storeImageUrl } from '../../utils/store'

const appStore = useAppStore()
const userStore = useUserStore()
const storeId = ref('')
const rating = ref(5)
const content = ref('')
const submitting = ref(false)
const loading = ref(true)
const loadError = ref('')
const selectedStore = computed(() => appStore.findStore(storeId.value))
const selectableStores = computed(() => appStore.activeSchoolStores.filter((store) => store.isEaten))

onLoad((query) => {
  if (typeof query?.storeId === 'string') storeId.value = query.storeId
})

async function loadExistingReview() {
  loading.value = true
  loadError.value = ''
  try {
    await appStore.initialize()
    if (!storeId.value || !selectableStores.value.some((store) => store.id === storeId.value)) {
      storeId.value = selectableStores.value[0]?.id || ''
    }
    const existing = (await getAllMyReviews()).items.find((review) => review.store.id === storeId.value)
    if (existing) {
      rating.value = existing.rating
      content.value = existing.content
    }
  } catch (cause) {
    loadError.value = cause instanceof ApiClientError ? cause.message : '评价页面加载失败，请重试'
    uni.showToast({ title: cause instanceof ApiClientError ? cause.message : '评价页面加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function submit() {
  const text = content.value.trim()
  if (!storeId.value) return uni.showToast({ title: '请先选择店铺', icon: 'none' })
  if (rating.value < 1 || rating.value > 5) return uni.showToast({ title: '评分范围为 1-5 分', icon: 'none' })
  if (!text) return uni.showToast({ title: '写点真实感受吧', icon: 'none' })
  if (text.length > 500) return uni.showToast({ title: '评价不能超过 500 字', icon: 'none' })
  if (submitting.value) return
  submitting.value = true
  try {
    await saveMyReview(storeId.value, { rating: rating.value, content: text })
    await Promise.all([userStore.refreshProfile().catch(() => undefined), appStore.refreshStore(storeId.value).catch(() => undefined)])
    uni.showToast({ title: '评价已提交', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 450)
  } catch (cause) {
    uni.showToast({ title: cause instanceof ApiClientError ? cause.message : '评价提交失败', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

onShow(() => { void loadExistingReview() })
</script>

<template>
  <view class="page-shell create-page" :class="appStore.fontClass"><PageHeader title="评价店铺" back /><view v-if="loading" class="page-state">正在加载评价页面…</view><view v-else-if="loadError" class="page-state"><text>{{ loadError }}</text><button class="retry-button" @tap="loadExistingReview">重新加载</button></view><view v-else class="page-pad"><template v-if="selectableStores.length"><text class="label">评价哪家店？</text><scroll-view scroll-x class="store-picker" :show-scrollbar="false"><view v-for="store in selectableStores" :key="store.id" class="store-chip" :class="{ active: store.id === storeId }" @tap="storeId = store.id"><FallbackImage :src="storeImageUrl(store)" /><text>{{ store.name }}</text></view></scroll-view><text class="label rating-label">打个分</text><view class="rating-row"><text v-for="item in 5" :key="item" class="star" :class="{ active: item <= rating }" @tap="rating = item">★</text><text class="rating-copy">{{ rating }} 分</text></view><text class="label">说说感受</text><textarea v-model="content" class="review-input" maxlength="500" placeholder="味道、价格、位置都可以写下来" placeholder-class="review-placeholder" /><text class="counter">{{ content.length }}/500</text><button class="submit-button" :disabled="submitting" @tap="submit">{{ submitting ? '提交中…' : '提交评价' }}</button><text v-if="selectedStore" class="selected-store">当前：{{ selectedStore.name }} · {{ selectedStore.area || '未分区' }}</text></template><EmptyState v-else title="还没有可评价的店铺" description="完成一次带图片打卡后，就可以为这家店写评价了" /></view></view>
</template>

<style scoped>
.create-page { background: var(--page); }.page-pad { padding: 30rpx; }.label { display: block; margin-bottom: 14rpx; color: var(--ink); font-size: 28rpx; font-weight: 800; }.rating-label { margin-top: 30rpx; }.store-picker { width: 100%; white-space: nowrap; }.store-chip { display: inline-flex; align-items: center; width: 260rpx; margin-right: 14rpx; padding: 12rpx; border: 1rpx solid transparent; border-radius: 12rpx; background: #fff; }.store-chip.active { border-color: var(--brand); background: #f2faf5; }.store-chip image { width: 62rpx; height: 62rpx; border-radius: 10rpx; }.store-chip text { max-width: 170rpx; margin-left: 12rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 23rpx; }.rating-row { display: flex; align-items: center; gap: 12rpx; margin-bottom: 30rpx; }.star { color: #d7dfda; font-size: 54rpx; }.star.active { color: var(--amber); }.rating-copy { margin-left: 8rpx; color: var(--muted); font-size: 24rpx; }.review-input { width: 100%; min-height: 260rpx; padding: 22rpx; border-radius: 12rpx; background: #fff; font-size: 26rpx; line-height: 1.6; }.review-placeholder { color: #9aa9a1; }.counter { display: block; margin-top: 8rpx; color: var(--muted); font-size: 21rpx; text-align: right; }.submit-button { width: 100%; height: 84rpx; margin-top: 28rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; }.submit-button[disabled] { opacity: .65; }.selected-store { display: block; margin-top: 20rpx; color: var(--muted); font-size: 22rpx; text-align: center; }
.page-state { display: flex; align-items: center; justify-content: center; min-height: 560rpx; padding: 40rpx; color: var(--muted); flex-direction: column; text-align: center; }.retry-button { margin-top: 22rpx; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
</style>
