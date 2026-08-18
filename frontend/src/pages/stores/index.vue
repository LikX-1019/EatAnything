<script setup lang="ts">
import { computed, ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import StoreRow from '../../components/StoreRow.vue'
import EmptyState from '../../components/EmptyState.vue'
// #ifndef MP-WEIXIN
import StickerTabBar from '../../components/StickerTabBar.vue'
// #endif
import { useAppStore } from '../../stores/useAppStore'
import type { StoreItem } from '../../types'

const appStore = useAppStore()
const keyword = ref('')
const sort = ref<'all' | 'score' | 'favorite'>('all')
const filteredStores = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  let list = appStore.activeAreaStores.filter((store) => !query || [store.name, store.category, store.address].some((field) => field.toLowerCase().includes(query)))
  if (sort.value === 'score') list = [...list].sort((a, b) => b.score - a.score)
  if (sort.value === 'favorite') list = list.filter((store) => store.favorite)
  return list
})

function showStoreActions(store: StoreItem) {
  appStore.recordVisit(store.id)
  uni.showActionSheet({
    itemList: [store.favorite ? '取消收藏' : '加入收藏', store.eaten ? '标记为未吃过' : '标记为吃过'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) appStore.toggleFavorite(store.id)
      if (tapIndex === 1) appStore.toggleEaten(store.id)
    }
  })
}
</script>

<template>
  <view class="page-shell stores-page" :class="appStore.fontClass">
    <PageHeader title="所有店铺" />
    <view class="page-pad">
      <view class="school-line"><text>📍 {{ appStore.activeSchool?.name }}</text><text class="area-name">{{ appStore.activeArea?.name }}</text><text class="leaf">❀</text></view>
      <scroll-view scroll-x class="area-tabs" :show-scrollbar="false">
        <view v-for="area in appStore.activeAreas" :key="area.id" class="area-tab" :class="{ active: area.id === appStore.selectedAreaId }" @tap="appStore.selectArea(area.id)">{{ area.name }}</view>
      </scroll-view>
      <view class="search-box"><text class="search-icon">⌕</text><input v-model="keyword" class="search-input" placeholder="搜索店铺、分类或地址" placeholder-class="search-placeholder" /><text v-if="keyword" class="clear-search" @tap="keyword = ''">×</text></view>
      <scroll-view scroll-x class="filters" :show-scrollbar="false">
        <view class="filter" :class="{ active: sort === 'all' }" @tap="sort = 'all'">全部 {{ appStore.activeAreaStores.length }}</view>
        <view class="filter" :class="{ active: sort === 'score' }" @tap="sort = 'score'">评分高</view>
        <view class="filter" :class="{ active: sort === 'favorite' }" @tap="sort = 'favorite'">已收藏</view>
      </scroll-view>
      <view v-if="filteredStores.length" class="store-list"><StoreRow v-for="store in filteredStores" :key="store.id" :store="store" @press="showStoreActions" /></view>
      <EmptyState v-else title="当前区域没有匹配店铺" description="换个关键词或切换区域试试" />
    </view>
    <!-- #ifndef MP-WEIXIN -->
    <StickerTabBar />
    <!-- #endif -->
  </view>
</template>

<style scoped>
.stores-page { background-color: transparent; background-image: linear-gradient(rgba(215,181,137,.18) 1rpx, transparent 1rpx), linear-gradient(90deg, rgba(215,181,137,.16) 1rpx, transparent 1rpx); background-size: 40rpx 40rpx; }
.page-pad { padding: 8rpx 30rpx; }
.school-line { position: relative; display: flex; align-items: baseline; gap: 14rpx; width: fit-content; margin: 8rpx auto 20rpx; padding: 12rpx 34rpx; border: 1rpx solid #e1c9a7; background: #fff5dc; color: var(--brand-deep); font-size: 31rpx; font-weight: 900; box-shadow: var(--paper-shadow); transform: rotate(.6deg); }
.school-line::before { position: absolute; top: -9rpx; left: -8rpx; width: 66rpx; height: 22rpx; background: rgba(235,190,132,.52); content: ''; transform: rotate(-14deg); }
.area-name { color: var(--muted); font-size: 25rpx; font-weight: 400; }.leaf { margin-left: 8rpx; color: var(--brand); }
.area-tabs, .filters { width: 100%; white-space: nowrap; }
.area-tab, .filter { display: inline-flex; align-items: center; height: 62rpx; margin-right: 12rpx; padding: 0 23rpx; border: 1rpx dashed #d4b994; border-radius: 8rpx 13rpx 7rpx 11rpx; background: #fffaf0; color: #806955; font-size: 26rpx; }
.area-tab.active, .filter.active { border-style: solid; border-color: #dc8c7b; background: #f7d8cf; color: #a75245; font-weight: 900; box-shadow: 0 3rpx 0 #d49c90; }
.search-box { display: flex; align-items: center; height: 76rpx; margin: 20rpx 0 16rpx; padding: 0 22rpx; border: 1rpx solid #d8c3a5; border-radius: 26rpx 16rpx 24rpx 18rpx; background: rgba(255,250,238,.92); box-shadow: 0 4rpx 9rpx rgba(93,65,34,.08); }
.search-icon { margin-right: 12rpx; color: var(--muted); font-size: 42rpx; }
.search-input { min-width: 0; flex: 1; height: 76rpx; font-size: 29rpx; }
.search-placeholder { color: #aa927b; }
.clear-search { color: var(--muted); font-size: 38rpx; }
.filters { margin-bottom: 4rpx; }
.filter { height: 56rpx; padding: 0 19rpx; background: #f3ead9; font-size: 25rpx; }
.store-list { padding-bottom: 32rpx; }
</style>
