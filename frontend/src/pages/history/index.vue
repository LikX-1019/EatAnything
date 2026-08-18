<script setup lang="ts">
import EmptyState from '../../components/EmptyState.vue'
import { useAppStore } from '../../stores/useAppStore'
import PageHeader from '../../components/PageHeader.vue'
const appStore = useAppStore()
</script>

<template>
  <view class="page-shell history-page" :class="appStore.fontClass"><PageHeader title="历史记录" back /><view class="page-pad"><view v-if="appStore.history.length" class="timeline"><view v-for="item in appStore.history" :key="item.id" class="history-item"><view class="dot" :class="{ green: item.action === '到店打卡' }" /><image class="history-image" :src="appStore.findStore(item.storeId)?.image" mode="aspectFill" /><view class="history-copy"><text class="history-name">{{ appStore.findStore(item.storeId)?.name }}</text><text class="history-action">{{ item.action }} · {{ appStore.findArea(appStore.findStore(item.storeId))?.name }}</text><text class="history-date">{{ item.date }}</text></view></view></view><EmptyState v-else title="还没有历史记录" description="浏览或抽取店铺后会显示在这里" /></view></view>
</template>

<style scoped>
.history-page { background: #fff; }
.page-pad { padding: 28rpx 30rpx; }
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
