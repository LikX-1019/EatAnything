<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

const tabs = [
  { path: 'pages/home/index', url: '/pages/home/index', label: '首页', icon: '/static/tabbar/house.png', activeIcon: '/static/tabbar/house-active.png' },
  { path: 'pages/stores/index', url: '/pages/stores/index', label: '所有店铺', icon: '/static/tabbar/store.png', activeIcon: '/static/tabbar/store-active.png' },
  { path: 'pages/eaten/index', url: '/pages/eaten/index', label: '吃过的店铺', icon: '/static/tabbar/heart.png', activeIcon: '/static/tabbar/heart-active.png' },
  { path: 'pages/profile/index', url: '/pages/profile/index', label: '我的', icon: '/static/tabbar/user-round.png', activeIcon: '/static/tabbar/user-round-active.png' }
]

const activeTabPath = ref('')

function getRoutePath() {
  const pages = getCurrentPages()
  return pages[pages.length - 1]?.route || 'pages/home/index'
}

const currentPath = computed(() => activeTabPath.value || getRoutePath())

function syncCurrentPath() {
  activeTabPath.value = getRoutePath()
}

function switchPage(url: string) {
  const path = url.replace(/^\//, '')
  activeTabPath.value = path
  uni.switchTab({
    url,
    fail: () => {
      // 部分 H5 运行时不会为自定义标签栏提供 switchTab。
      uni.reLaunch({ url, fail: syncCurrentPath })
    },
  })
}

onMounted(() => {
  syncCurrentPath()
  // #ifndef MP-WEIXIN
  uni.hideTabBar({ animation: false, fail: () => undefined })
  // #endif
})
onActivated(syncCurrentPath)
onShow(syncCurrentPath)
</script>

<template>
  <!-- #ifndef MP-WEIXIN -->
  <view class="sticker-tabbar" @touchmove.stop>
    <view class="torn-edge" />
    <button v-for="(tab, index) in tabs" :key="tab.path" class="tab-item" :class="[`tab-${index}`, { active: currentPath === tab.path }]" @tap="switchPage(tab.url)">
      <view class="icon-sticker" :class="`sticker-${index}`">
        <image :src="currentPath === tab.path ? tab.activeIcon : tab.icon" mode="aspectFit" />
      </view>
      <text>{{ tab.label }}</text>
    </button>
  </view>
  <!-- #endif -->
</template>

<style scoped>
.sticker-tabbar { position: fixed; z-index: 999; right: 14rpx; bottom: 0; left: 14rpx; display: flex; align-items: center; height: 116rpx; padding: 6rpx 8rpx 8rpx; border: 1rpx solid #ddc8a8; border-radius: 18rpx 14rpx 22rpx 16rpx; background-color: #fffaf0; background-image: radial-gradient(circle, rgba(164,122,75,.07) 1rpx, transparent 1.5rpx); background-size: 18rpx 18rpx; box-shadow: 0 -4rpx 14rpx rgba(92,65,34,.1), 0 4rpx 12rpx rgba(92,65,34,.08); }
.torn-edge { position: absolute; top: -10rpx; right: 10rpx; left: 10rpx; height: 12rpx; background: linear-gradient(135deg, transparent 6rpx, #fffaf0 0) 0 0 / 18rpx 12rpx repeat-x, linear-gradient(45deg, #fffaf0 6rpx, transparent 0) 9rpx 0 / 18rpx 12rpx repeat-x; }
.tab-item { position: relative; display: flex; align-items: center; flex: 1; flex-direction: column; justify-content: center; height: 98rpx; padding: 0; border: 0; border-radius: 0; background: transparent; color: #836d58; font-size: 23rpx; font-weight: 700; line-height: 1.2; box-shadow: none; }
.tab-item::after { display: none; border: 0; }
.icon-sticker { position: relative; display: flex; align-items: center; justify-content: center; width: 56rpx; height: 52rpx; margin-bottom: 4rpx; }
.icon-sticker image { width: 43rpx; height: 43rpx; }
.active { color: #493424; font-weight: 900; }
.sticker-0 { transform: rotate(-1deg); }.sticker-1 { transform: rotate(1deg); }.sticker-2 { transform: rotate(-1deg); }.sticker-3 { transform: rotate(2deg); }
</style>
