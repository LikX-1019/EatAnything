<script setup lang="ts">
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { ApiClientError } from '../../api/types'
import EmptyState from '../../components/EmptyState.vue'
import { useAppStore } from '../../stores/useAppStore'
import PageHeader from '../../components/PageHeader.vue'
import { storeImageUrl } from '../../utils/store'
import FallbackImage from '../../components/FallbackImage.vue'
const appStore = useAppStore()
const loading = ref(true)
const errorMessage = ref('')
function formatHistoryTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
async function loadHistory(refresh = false) {
  loading.value = !refresh
  errorMessage.value = ''
  try { if (refresh) await appStore.refresh(); else await appStore.initialize() }
  catch (error) { errorMessage.value = error instanceof ApiClientError ? error.message : '历史记录加载失败，请重试'; uni.showToast({ title: errorMessage.value, icon: 'none' }) }
  finally { loading.value = false; if (refresh) uni.stopPullDownRefresh() }
}
onShow(() => { void loadHistory() })
onPullDownRefresh(() => { void loadHistory(true) })
</script>

<template>
  <view class="page-shell history-page" :class="appStore.fontClass"><PageHeader title="历史记录" back /><view class="page-pad"><view v-if="loading" class="page-state">正在加载历史记录…</view><view v-else-if="errorMessage" class="page-state"><text>{{ errorMessage }}</text><button class="retry-button" @tap="loadHistory()">重新加载</button></view><template v-else><view v-if="appStore.history.length" class="timeline"><view v-for="item in appStore.history" :key="item.id" class="history-item"><view class="dot" :class="{ green: item.action === 'DETAIL_VIEW' }" /><FallbackImage class="history-image" :src="storeImageUrl(item.store)" /><view class="history-copy"><text class="history-name">{{ item.store.name }}</text><text class="history-action">{{ item.action === 'RANDOM_PICK' ? '随机抽取' : '浏览店铺' }} · {{ item.store.area || '未分区' }}</text><text class="history-date">{{ formatHistoryTime(item.occurredAt) }}</text></view></view></view><EmptyState v-else title="暂无抽店或浏览记录" description="浏览或抽取店铺后会显示在这里" /></template></view></view>
</template>

<style scoped>
.history-page { background: #fff; }
.page-pad { padding: 28rpx 30rpx; }
.page-state { padding: 80rpx 20rpx; color: var(--muted); text-align: center; }.retry-button { display: block; margin: 22rpx auto 0; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
.timeline { position: relative; padding-left: 12rpx; }
.timeline::before { position: absolute; top: 30rpx; bottom: 30rpx; left: 18rpx; width: 2rpx; background: var(--line); content: ''; }
.history-item { position: relative; display: flex; min-height: 144rpx; padding: 14rpx 0 22rpx 42rpx; border-bottom: 1rpx solid var(--line); }
.dot { position: absolute; top: 34rpx; left: 8rpx; width: 20rpx; height: 20rpx; border: 4rpx solid #fff; border-radius: 50%; background: var(--amber); box-shadow: 0 0 0 2rpx #f7d896; }
.dot.green { background: var(--brand); box-shadow: 0 0 0 2rpx #b6deca; }
.history-image { width: 108rpx; height: 108rpx; border-radius: 10rpx; }
.history-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; justify-content: center; padding-left: 20rpx; }
.history-name { font-size: 28rpx; font-weight: 800; }
.history-action, .history-date { margin-top: 8rpx; color: var(--muted); font-size: 22rpx; }
</style>
