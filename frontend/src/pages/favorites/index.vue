<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { ApiClientError } from '../../api/types'
import EmptyState from '../../components/EmptyState.vue'
import StoreRow from '../../components/StoreRow.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'
import type { StoreItem } from '../../types'

const appStore = useAppStore()
onShow(async () => {
  try { await appStore.initialize() }
  catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '店铺数据加载失败', icon: 'none' }) }
})
function manage(store: StoreItem) {
  uni.showActionSheet({
    itemList: ['取消收藏', store.isEaten ? '标记为未吃过' : '标记为吃过'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) appStore.toggleFavorite(store.id)
      if (tapIndex === 1) appStore.toggleEaten(store.id)
    }
  })
}
</script>

<template>
  <view class="page-shell favorites-page" :class="appStore.fontClass">
    <PageHeader title="我的收藏" back />
    <view class="page-pad">
      <view class="school-line">{{ appStore.activeSchool?.name }} <text>⌄</text></view>
      <scroll-view scroll-x class="area-tabs" :show-scrollbar="false"><view v-for="area in appStore.activeAreas" :key="area.id" class="area-tab" :class="{ active: area.id === appStore.selectedAreaId }" @tap="appStore.selectArea(area.id)">{{ area.name }}</view></scroll-view>
      <scroll-view scroll-x class="filters" :show-scrollbar="false"><view class="filter active">已收藏</view><view class="filter">全部</view><view class="filter">评分高</view></scroll-view>
      <text class="summary">共收藏 {{ appStore.activeSchoolFavoriteStores.length }} 家校园店铺</text>
      <view v-if="appStore.activeSchoolFavoriteStores.length" class="list"><StoreRow v-for="store in appStore.activeSchoolFavoriteStores" :key="store.id" :store="store" @press="manage" /></view>
      <EmptyState v-else title="还没有收藏" description="把喜欢的校园店铺先收藏起来" />
    </view>
  </view>
</template>

<style scoped>
.favorites-page { background: var(--page); }
.page-pad { padding: 0 30rpx; }
.school-line { margin: 8rpx 0 18rpx; color: var(--brand); font-size: 25rpx; font-weight: 800; }
.school-line text { margin-left: 6rpx; font-size: 28rpx; }
.area-tabs, .filters { width: 100%; white-space: nowrap; }
.area-tab, .filter { display: inline-flex; align-items: center; height: 60rpx; margin-right: 12rpx; padding: 0 20rpx; border: 1rpx solid var(--line); border-radius: 30rpx; background: #fff; color: #5d7569; font-size: 22rpx; }
.area-tab.active, .filter.active { border-color: var(--brand); background: var(--brand); color: #fff; font-weight: 700; }
.filters { margin-top: 14rpx; }
.summary { display: block; margin: 20rpx 0 4rpx; color: var(--muted); font-size: 21rpx; }
.list { padding-bottom: 30rpx; }
</style>
