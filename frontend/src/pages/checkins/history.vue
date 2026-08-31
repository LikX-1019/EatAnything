<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ApiClientError } from '../../api/types'
import type { CheckInItem } from '../../api/checkins'
import EmptyState from '../../components/EmptyState.vue'
import FallbackImage from '../../components/FallbackImage.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'
import { storeImageUrl } from '../../utils/store'

const appStore = useAppStore()
const storeId = ref('')
const loading = ref(true)
const errorMessage = ref('')
const resolvedImages = ref<Record<string, string>>({})

const store = computed(() => appStore.findStore(storeId.value))
const records = computed(() => appStore.checkIns
  .filter((item) => item.storeId === storeId.value)
  .sort((a, b) => new Date(b.checkedAt).getTime() - new Date(a.checkedAt).getTime()))

onLoad((query) => {
  storeId.value = typeof query?.storeId === 'string' ? query.storeId : ''
})

function formatCheckInTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return String(date.getFullYear()) + '年' + String(date.getMonth() + 1) + '月' + String(date.getDate()) + '日 ' + String(date.getHours()).padStart(2, '0') + ':' + String(date.getMinutes()).padStart(2, '0')
}

function setResolvedImage(recordId: string, source: string) {
  resolvedImages.value = { ...resolvedImages.value, [recordId]: source }
}

function previewRecord(record: CheckInItem) {
  const source = resolvedImages.value[record.id] || record.photoUrl
  uni.previewImage({ current: source, urls: [source] })
}

function writeReview() {
  if (!store.value) return
  uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(storeId.value)}` })
}

async function load(refresh = false) {
  loading.value = !refresh
  errorMessage.value = ''
  try {
    if (refresh) await appStore.refresh()
    else await appStore.initialize()
    if (!storeId.value) errorMessage.value = '店铺参数无效'
  } catch (error) {
    errorMessage.value = error instanceof ApiClientError ? error.message : '打卡记录加载失败，请重试'
  } finally {
    loading.value = false
    if (refresh) uni.stopPullDownRefresh()
  }
}

onShow(() => { if (storeId.value) void load() })
onPullDownRefresh(() => { void load(true) })
</script>

<template>
  <view class="page-shell checkin-history-page" :class="appStore.fontClass">
    <PageHeader title="打卡记录" back />
    <view class="page-pad">
      <view v-if="store" class="store-banner">
        <FallbackImage class="store-banner-image" :src="storeImageUrl(store)" />
        <view class="store-banner-copy"><text class="store-banner-name">{{ store.name }}</text><text class="store-banner-area">{{ store.area || '未分区' }} · 共 {{ records.length }} 次打卡</text></view>
        <button class="banner-review-button" @tap="writeReview">写评价</button>
      </view>
      <view v-if="loading" class="page-state">正在加载打卡记录…</view>
      <view v-else-if="errorMessage" class="page-state"><text>{{ errorMessage }}</text><button class="retry-button" @tap="load">重新加载</button></view>
      <template v-else>
        <view v-if="records.length" class="record-list">
          <view v-for="record in records" :key="record.id" class="record-card">
            <FallbackImage class="record-image" :src="record.photoUrl" @tap="previewRecord(record)" @resolved="setResolvedImage(record.id, $event)" />
            <view class="record-footer"><text class="record-time">打卡于 {{ formatCheckInTime(record.checkedAt) }}</text><text v-if="record.note" class="record-note">{{ record.note }}</text><text class="record-action">点击图片查看大图</text></view>
          </view>
        </view>
        <EmptyState v-else title="还没有打卡记录" description="上传到店照片后，会在这里留下记录" />
      </template>
    </view>
  </view>
</template>

<style scoped>
.checkin-history-page { background: transparent; }
.page-pad { padding: 22rpx 30rpx 48rpx; }
.store-banner { display: flex; align-items: center; gap: 18rpx; padding: 16rpx; border: 1rpx solid #ddc5a3; border-radius: 12rpx 8rpx 14rpx 9rpx; background: #fffaf0; box-shadow: var(--paper-shadow); transform: rotate(-.3deg); }
.store-banner-image { flex: 0 0 auto; width: 112rpx; height: 92rpx; border: 5rpx solid #fff; background: #f2e8d5; box-shadow: 0 3rpx 8rpx rgba(90,65,40,.15); }
.store-banner-copy { min-width: 0; }.store-banner-name { display: block; overflow: hidden; color: var(--ink); font-size: 31rpx; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }.store-banner-area { display: block; margin-top: 8rpx; color: var(--muted); font-size: 23rpx; }
.banner-review-button { flex: 0 0 auto; height: 58rpx; margin-left: auto; padding: 0 20rpx; border: 0; border-radius: 8rpx; background: var(--brand); color: #fff; font-size: 24rpx; line-height: 58rpx; }
.banner-review-button::after { border: 0; }
.page-state { padding: 90rpx 20rpx; color: var(--muted); font-size: 27rpx; text-align: center; }.retry-button { display: block; margin: 22rpx auto 0; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
.record-list { display: flex; flex-direction: column; gap: 22rpx; margin-top: 24rpx; }.record-card { padding: 12rpx 12rpx 16rpx; border: 1rpx solid #ddc6a5; border-radius: 8rpx 14rpx 10rpx 16rpx; background: #fffaf0; box-shadow: var(--paper-shadow); transform: rotate(-.25deg); }.record-card:nth-child(even) { background: #f0f5e5; transform: rotate(.3deg); }.record-image { width: 100%; height: 390rpx; background: #f2e8d5; }.record-footer { display: flex; flex-direction: column; padding: 14rpx 8rpx 0; }.record-time { color: var(--ink); font-size: 27rpx; font-weight: 800; }.record-note { margin-top: 8rpx; color: #5f6c63; font-size: 24rpx; line-height: 1.5; }.record-action { margin-top: 8rpx; color: var(--muted); font-size: 21rpx; }
</style>
