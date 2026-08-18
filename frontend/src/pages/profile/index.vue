<script setup lang="ts">
import { onShareAppMessage } from '@dcloudio/uni-app'
import PageHeader from '../../components/PageHeader.vue'
// #ifndef MP-WEIXIN
import StickerTabBar from '../../components/StickerTabBar.vue'
// #endif
import { useAppStore } from '../../stores/useAppStore'

const appStore = useAppStore()
const menuItems = [
  { key: 'favorites', icon: '☆', label: '我的收藏', path: '/pages/favorites/index', color: '#f0a028' },
  { key: 'reviews', icon: '●●●', label: '我的评价', path: '/pages/reviews/index', color: '#46a8d7' },
  { key: 'history', icon: '◷', label: '历史记录', path: '/pages/history/index', color: '#47aeb6' },
  { key: 'share', icon: '⌯', label: '推荐给好友', color: '#ed6d82' },
  { key: 'settings', icon: '⚙', label: '设置', path: '/pages/settings/index', color: '#8f918e' },
  { key: 'about', icon: 'ⓘ', label: '关于我们', color: '#708dcf' }
]

function handleMenu(item: typeof menuItems[number]) {
  if (item.path) {
    uni.navigateTo({ url: item.path })
    return
  }
  uni.showModal({
    title: item.label,
    content: item.key === 'settings' ? '当前为校园吃什么演示版本。' : '校园吃什么，帮你快速找到下一顿。',
    showCancel: false,
    confirmText: '知道了'
  })
}

onShareAppMessage(() => ({ title: '校园吃什么？让它帮你选一家', path: '/pages/home/index' }))
</script>

<template>
  <view class="page-shell profile-page" :class="appStore.fontClass">
    <PageHeader title="我的" dark />
    <view class="profile-hero">
      <view class="identity">
        <view class="avatar">👩🏻‍🍳</view>
        <view class="identity-copy">
          <text class="profile-name">干饭小能手</text>
          <text class="profile-slogan">干饭是第一生产力！</text>
          <text class="level">Lv.3</text>
        </view>
      </view>
      <view class="stats">
        <view class="stat"><text>{{ appStore.activeSchoolEatenStores.length }}</text><small>吃过店铺</small></view>
        <view class="divider" />
        <view class="stat"><text>{{ appStore.activeSchoolStores.length - appStore.activeSchoolEatenStores.length }}</text><small>想去的店铺</small></view>
        <view class="divider" />
        <view class="stat"><text>{{ appStore.activeSchoolFavoriteStores.length }}</text><small>收藏的店铺</small></view>
      </view>
    </view>
    <view class="menu-list">
      <template v-for="item in menuItems" :key="item.key">
        <button v-if="item.key === 'share'" class="menu-row share-row" open-type="share">
          <view class="menu-icon share-icon" :style="{ color: item.color }">{{ item.icon }}</view>
          <text class="menu-label">{{ item.label }}</text>
          <text class="arrow">›</text>
        </button>
        <view v-else class="menu-row" @tap="handleMenu(item)">
          <view class="menu-icon" :class="`menu-icon-${item.key}`" :style="{ color: item.color }">{{ item.icon }}</view>
          <text class="menu-label">{{ item.label }}</text>
          <text class="arrow">›</text>
        </view>
      </template>
    </view>
    <!-- #ifndef MP-WEIXIN -->
    <StickerTabBar />
    <!-- #endif -->
  </view>
</template>

<style scoped>
.profile-page { position: relative; background: transparent; }
.profile-page::after { position: fixed; z-index: 0; right: 15rpx; bottom: 130rpx; color: #78966c; font-size: 68rpx; content: '🌿'; transform: rotate(-14deg); }
.profile-hero { position: relative; z-index: 1; margin: 14rpx 26rpx 0; padding: 22rpx 18rpx 20rpx; border: 1rpx solid #e1c8a5; border-radius: 5rpx 12rpx 7rpx 9rpx; background: #fffaf0; color: var(--ink); box-shadow: var(--paper-shadow); }
.profile-hero::before, .profile-hero::after { position: absolute; top: -11rpx; width: 84rpx; height: 27rpx; background: rgba(228,192,142,.48); content: ''; }.profile-hero::before { left: 25rpx; transform: rotate(-7deg); }.profile-hero::after { right: 25rpx; transform: rotate(7deg); }
.identity { display: flex; align-items: center; padding: 16rpx 16rpx 30rpx; }
.avatar { display: flex; align-items: center; justify-content: center; width: 126rpx; height: 126rpx; border: 5rpx solid #fff; border-radius: 50%; background: #f7dfc9; font-size: 57rpx; box-shadow: 0 0 0 2rpx #e7c7ad, 0 5rpx 10rpx rgba(95,62,37,.12); }
.identity-copy { padding-left: 24rpx; }
.profile-name, .profile-slogan { display: block; }
.profile-name { font-size: 41rpx; font-weight: 900; }.profile-slogan { margin-top: 8rpx; color: var(--muted); font-size: 25rpx; }.level { width: fit-content; margin-top: 8rpx; padding: 4rpx 11rpx; border-radius: 8rpx; background: #ec9350; color: #fff; font-size: 21rpx; font-weight: 900; }
.stats { display: flex; align-items: center; padding: 22rpx 10rpx; border: 2rpx dashed #d69c71; border-radius: 17rpx; background: rgba(255,253,246,.8); color: var(--ink); }
.stat { display: flex; flex: 1; align-items: center; flex-direction: column; }
.stat text { font-size: 39rpx; font-weight: 900; }.stat small { margin-top: 7rpx; color: #6d5745; font-size: 23rpx; }
.divider { width: 1rpx; height: 58rpx; background: var(--line); }
.menu-list { position: relative; z-index: 1; margin: 30rpx 26rpx 0; padding: 10rpx 24rpx; border: 1rpx solid #e0c9aa; border-radius: 10rpx 6rpx 13rpx 7rpx; background-color: #fffaf0; background-image: linear-gradient(rgba(216,184,142,.1) 1rpx, transparent 1rpx); background-size: 100% 92rpx; box-shadow: var(--paper-shadow); transform: rotate(-.15deg); }
.menu-list::before { position: absolute; top: -12rpx; right: 52rpx; width: 100rpx; height: 29rpx; background: rgba(239,180,143,.48); content: ''; transform: rotate(4deg); }.menu-row { display: flex; align-items: center; justify-content: flex-start; width: 100%; height: 92rpx; padding: 0; border: 0; border-bottom: 1rpx solid #eadfce; background: transparent; color: var(--ink); text-align: left; }
.menu-icon { display: flex; align-items: center; justify-content: center; width: 54rpx; font-size: 29rpx; font-weight: 800; }
.menu-icon-reviews { position: relative; color: transparent !important; font-size: 0; }
.menu-icon-reviews::before { width: 36rpx; height: 29rpx; border-radius: 15rpx; background: radial-gradient(circle at 28% 50%, #fff 0 2rpx, transparent 3rpx), radial-gradient(circle at 50% 50%, #fff 0 2rpx, transparent 3rpx), radial-gradient(circle at 72% 50%, #fff 0 2rpx, transparent 3rpx), #46a8d7; content: ''; }
.menu-icon-reviews::after { position: absolute; bottom: 7rpx; left: 10rpx; border-top: 8rpx solid #46a8d7; border-right: 7rpx solid transparent; content: ''; transform: rotate(18deg); }
.share-icon { letter-spacing: -8rpx; transform: rotate(-32deg); }
.menu-label { flex: 1; padding-left: 16rpx; font-size: 31rpx; }
.arrow { color: #a98c70; font-size: 40rpx; }
.share-row { overflow: visible; border-radius: 0; box-shadow: none; }
.share-row::after { display: none; border: 0; }
.menu-row:last-child { border-bottom: 0; }
</style>
