<script setup lang="ts">
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ApiClientError } from '../../api/types'
import PageHeader from '../../components/PageHeader.vue'
import EmptyState from '../../components/EmptyState.vue'
// #ifndef MP-WEIXIN
import StickerTabBar from '../../components/StickerTabBar.vue'
// #endif
import { useAppStore } from '../../stores/useAppStore'
import type { StoreItem } from '../../types'
import { storeImageUrl } from '../../utils/store'
import { syncTabBarSelected } from '../../utils/tabbar'
import FallbackImage from '../../components/FallbackImage.vue'

const appStore = useAppStore()
const mode = ref<'all' | 'eaten' | 'todo'>('all')
const checkingStoreId = ref<string | null>(null)
const resolvedCheckInImages = ref<Record<string, string>>({})
const loading = ref(true)
const errorMessage = ref('')
const eatenCount = computed(() => appStore.activeAreaStores.filter((store) => store.isEaten).length)
const list = computed(() => {
  const areaStores = appStore.activeAreaStores
  return mode.value === 'eaten'
    ? areaStores.filter((store) => store.isEaten)
    : mode.value === 'todo'
      ? areaStores.filter((store) => !store.isEaten)
      : areaStores
})

function chooseCheckInImage(): Promise<string | null> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (result) => resolve(result.tempFilePaths[0] || null),
      fail: (error) => {
        if (error.errMsg?.toLowerCase().includes('cancel')) resolve(null)
        else reject(new ApiClientError(error.errMsg || '选择图片失败', { code: 'IMAGE_PICK_FAILED', cause: error }))
      },
    })
  })
}

async function toggle(store: StoreItem) {
  if (store.isEaten || checkingStoreId.value) return
  try {
    const filePath = await chooseCheckInImage()
    if (!filePath) return
    checkingStoreId.value = store.id
    await appStore.createCheckIn(store.id, filePath)
    promptReviewAfterCheckIn(store)
  } catch (error) {
    uni.showToast({ title: error instanceof ApiClientError ? error.message : '打卡失败，请重试', icon: 'none' })
  } finally {
    checkingStoreId.value = null
  }
}
function promptReviewAfterCheckIn(store: StoreItem) {
  uni.showModal({
    title: '打卡成功',
    content: `已打卡「${store.name}」，是否立即评价这家店？`,
    confirmText: '去评价',
    cancelText: '稍后再说',
    success: ({ confirm }) => {
      if (confirm) uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(store.id)}` })
    },
  })
}
function formatCheckInTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function storeCheckInTime(storeId: string): string {
  const checkIn = appStore.latestCheckInForStore(storeId)
  return checkIn ? formatCheckInTime(checkIn.checkedAt) : ''
}
function setResolvedCheckInImage(storeId: string, source: string) {
  resolvedCheckInImages.value = { ...resolvedCheckInImages.value, [storeId]: source }
}
function previewStoreCheckIn(store: StoreItem) {
  const checkIn = appStore.latestCheckInForStore(store.id)
  if (!checkIn) return
  uni.previewImage({ urls: [resolvedCheckInImages.value[store.id] || checkIn.photoUrl] })
}
async function replaceStoreCheckIn(store: StoreItem) {
  const checkIn = appStore.latestCheckInForStore(store.id)
  if (!checkIn || checkingStoreId.value) return
  try {
    const filePath = await chooseCheckInImage()
    if (!filePath) return
    checkingStoreId.value = store.id
    await appStore.updateCheckIn(checkIn.id, filePath)
    delete resolvedCheckInImages.value[store.id]
    uni.showToast({ title: '打卡图片已更新', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof ApiClientError ? error.message : '修改打卡图片失败', icon: 'none' })
  } finally {
    checkingStoreId.value = null
  }
}
async function addStoreCheckIn(store: StoreItem) {
  if (checkingStoreId.value) return
  try {
    const filePath = await chooseCheckInImage()
    if (!filePath) return
    checkingStoreId.value = store.id
    await appStore.createCheckIn(store.id, filePath)
    uni.showToast({ title: '已添加新的打卡记录', icon: 'success' })
  } catch (error) {
    uni.showToast({ title: error instanceof ApiClientError ? error.message : '添加打卡记录失败', icon: 'none' })
  } finally {
    checkingStoreId.value = null
  }
}
function openCheckInHistory(store: StoreItem) {
  uni.navigateTo({ url: `/pages/checkins/history?storeId=${encodeURIComponent(store.id)}` })
}
function openStoreCheckIn(store: StoreItem) {
  const checkIn = appStore.latestCheckInForStore(store.id)
  if (!checkIn) return toggle(store)
  uni.showActionSheet({
    itemList: ['查看打卡记录', '查看大图', '修改图片', '添加打卡记录', '评价该店铺'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) openCheckInHistory(store)
      else if (tapIndex === 1) previewStoreCheckIn(store)
      else if (tapIndex === 2) void replaceStoreCheckIn(store)
      else if (tapIndex === 3) void addStoreCheckIn(store)
      else if (tapIndex === 4) uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(store.id)}` })
    },
  })
}
async function loadEaten(refresh = false) {
  loading.value = !refresh
  errorMessage.value = ''
  try { if (refresh) await appStore.refresh(); else await appStore.initialize() }
  catch (error) { errorMessage.value = error instanceof ApiClientError ? error.message : '吃过列表加载失败，请重试'; uni.showToast({ title: errorMessage.value, icon: 'none' }) }
  finally { loading.value = false; if (refresh) uni.stopPullDownRefresh() }
}
onShow(() => {
  syncTabBarSelected(2)
  void loadEaten()
})
onPullDownRefresh(() => { void loadEaten(true) })
</script>

<template>
  <view class="page-shell eaten-page" :class="appStore.fontClass">
    <PageHeader title="吃过的店铺" />
    <view class="page-pad">
      <view class="school-line">🍀 {{ appStore.activeSchool?.name }} <text>⌄</text></view>
      <scroll-view scroll-x class="area-tabs" :show-scrollbar="false">
        <view v-for="area in appStore.activeAreas" :key="area.id" class="area-tab" :class="{ active: area.id === appStore.selectedAreaId }" @tap="appStore.selectArea(area.id)">{{ area.name }}</view>
      </scroll-view>
      <view class="segmented">
        <view v-for="item in [{ id: 'all', label: '全部' }, { id: 'eaten', label: '吃过' }, { id: 'todo', label: '待探索' }]" :key="item.id" class="segment" :class="{ active: mode === item.id }" @tap="mode = item.id as typeof mode">{{ item.label }}</view>
      </view>
      <view class="progress-copy"><text>{{ appStore.activeArea?.name }} 已完成探索</text><text>{{ eatenCount }} / {{ appStore.activeAreaStores.length }}</text></view>
      <view class="progress-line"><view :style="{ width: `${appStore.activeAreaStores.length ? (eatenCount / appStore.activeAreaStores.length) * 100 : 0}%` }" /></view>
      <view v-if="loading" class="page-state">正在加载吃过记录…</view><view v-else-if="errorMessage" class="page-state"><text>{{ errorMessage }}</text><button class="retry-button" @tap="loadEaten()">重新加载</button></view><view v-else-if="list.length" class="store-grid">
        <view v-for="store in list" :key="store.id" class="grid-card" :class="{ 'not-eaten': !store.isEaten }" @tap="openStoreCheckIn(store)">
          <view class="image-wrap"><FallbackImage class="grid-image" :src="appStore.latestCheckInForStore(store.id)?.photoUrl || storeImageUrl(store)" @tap.stop="openStoreCheckIn(store)" @resolved="setResolvedCheckInImage(store.id, $event)" /><text v-if="store.isEaten" class="check-mark">✓</text></view>
          <text class="grid-name single-line">{{ store.name }}</text>
          <text class="grid-address single-line">{{ appStore.latestCheckInForStore(store.id) ? `打卡于 ${storeCheckInTime(store.id)}` : checkingStoreId === store.id ? '上传中…' : '点击选择图片打卡' }}</text>
        </view>
      </view>
      <EmptyState v-else title="还没有打卡过店铺" description="去首页抽一家，开始你的校园足迹" />
    </view>
    <!-- #ifndef MP-WEIXIN -->
    <StickerTabBar />
    <!-- #endif -->
  </view>
</template>

<style scoped>
.eaten-page { background: transparent; }
.page-pad { padding: 0 30rpx; }
.page-state { padding: 80rpx 20rpx; color: var(--muted); text-align: center; }.retry-button { display: block; margin: 22rpx auto 0; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
.school-line { width: fit-content; margin: 6rpx auto 0; padding: 10rpx 24rpx; border: 1rpx solid #dcc4a4; background: #fff4d9; color: var(--brand-deep); font-size: 29rpx; font-weight: 900; box-shadow: var(--paper-shadow); transform: rotate(-.7deg); }
.school-line text { margin-left: 6rpx; font-size: 28rpx; }
.area-tabs { width: 100%; margin: 20rpx 0; white-space: nowrap; }
.area-tab { display: inline-flex; align-items: center; height: 60rpx; margin-right: 12rpx; padding: 0 22rpx; border: 1rpx dashed #d3b894; border-radius: 9rpx; background: #fffaf0; color: #826b57; font-size: 26rpx; }
.area-tab.active { border-style: solid; background: #f5d7cc; color: #a65245; font-weight: 800; }
.segmented { display: flex; padding: 5rpx; border: 1rpx solid #dfc9a8; border-radius: 11rpx; background: #eee1c9; }
.segment { flex: 1; padding: 15rpx 0; border-radius: 8rpx; color: var(--muted); font-size: 27rpx; text-align: center; }
.segment.active { background: #fffaf0; color: var(--brand); font-weight: 900; box-shadow: 0 3rpx 7rpx rgba(103,75,42,.1); }
.progress-copy { display: flex; justify-content: space-between; margin: 22rpx 0 8rpx; color: var(--muted); font-size: 25rpx; }
.progress-line { height: 10rpx; overflow: hidden; border-radius: 5rpx; background: #e7d9c3; }.progress-line view { height: 100%; background: var(--green); }
.store-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18rpx; padding: 24rpx 0; }
.grid-card { position: relative; overflow: visible; padding: 10rpx 10rpx 14rpx; border: 1rpx solid #dec7a8; border-radius: 12rpx 7rpx 15rpx 8rpx; background: #fff9ea; box-shadow: var(--paper-shadow); transform: rotate(-.6deg); }.grid-card:nth-child(even) { background: #eef4df; transform: rotate(.8deg); }.grid-card::before { position: absolute; z-index: 2; top: -10rpx; left: 34%; width: 65rpx; height: 24rpx; background: rgba(233,175,153,.55); content: ''; transform: rotate(-4deg); }
.image-wrap { position: relative; aspect-ratio: 1 / .82; overflow: hidden; }
.grid-image { width: 100%; height: 100%; border-radius: 7rpx; }
.check-mark { position: absolute; top: 8rpx; right: 8rpx; display: flex; align-items: center; justify-content: center; width: 42rpx; height: 42rpx; border: 3rpx solid #fff; border-radius: 50%; background: #67b46e; color: #fff; font-size: 25rpx; font-weight: 800; }
.grid-name, .grid-address { display: block; padding: 0 16rpx; }
.grid-name { margin-top: 15rpx; font-size: 30rpx; font-weight: 800; }
.grid-address { margin: 8rpx 0 17rpx; color: var(--muted); font-size: 24rpx; }
.not-eaten { background: #eeeae0 !important; }.not-eaten .grid-image { filter: saturate(.2); opacity: .58; }
.not-eaten .grid-name { color: #819088; }
</style>
