<script setup lang="ts">
const props = withDefaults(defineProps<{ title?: string; compact?: boolean; back?: boolean; dark?: boolean; weather?: boolean; backTabFallback?: string }>(), { title: '', compact: false, back: false, dark: false, weather: false, backTabFallback: '' })
const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 24
let navBarHeight = 44

try {
  const menuButton = uni.getMenuButtonBoundingClientRect()
  if (menuButton?.height && menuButton.top >= statusBarHeight) {
    navBarHeight = (menuButton.top - statusBarHeight) * 2 + menuButton.height
  }
} catch {
  // H5 无法获取微信胶囊按钮信息，使用 44px 模拟原生回退高度。
}

const headerHeight = statusBarHeight + navBarHeight
function goBack() {
  uni.navigateBack({
    fail: () => {
      if (!props.backTabFallback) return
      uni.switchTab({
        url: props.backTabFallback,
        fail: () => {
          uni.reLaunch({
            url: props.backTabFallback,
            fail: () => uni.showToast({ title: '返回失败，请稍后重试', icon: 'none' }),
          })
        },
      })
    },
  })
}
</script>

<template>
  <view class="page-header-spacer" :style="{ height: `${headerHeight}px` }" />
  <view class="page-header" :class="{ compact: props.compact, dark: props.dark }">
    <view :style="{ height: `${statusBarHeight}px` }" />
    <view v-if="props.title" class="title-row" :style="{ height: `${navBarHeight}px` }">
      <view v-if="props.back" class="back-button" @tap="goBack">‹</view>
      <view v-if="props.weather" class="header-weather">
        <text class="header-weather-icon">🌤️</text>
        <text class="header-weather-copy">28°C 多云</text>
      </view>
      <view class="title-sticker"><text class="tape" /><text class="title">{{ props.title }}</text><text class="doodle">✿</text></view>
    </view>
  </view>
</template>

<style scoped>
.page-header-spacer { width: 100%; flex: 0 0 auto; }
.page-header { position: fixed; z-index: 100; top: 0; right: 0; left: 0; width: 100%; background: rgba(248,240,223,.98); }
.title-row { position: relative; display: flex; align-items: center; justify-content: center; min-height: 76rpx; padding: 0 140rpx; }
.title-sticker { position: relative; display: flex; align-items: center; justify-content: center; min-width: 280rpx; height: 68rpx; padding: 0 58rpx 0 42rpx; border: 1rpx solid #ead9bf; background: #fff9e9; box-shadow: 0 5rpx 10rpx rgba(100,72,40,.1); transform: rotate(-.6deg); }
.title-sticker::after { position: absolute; right: -10rpx; bottom: -7rpx; width: 45rpx; height: 22rpx; background: rgba(239,164,139,.46); content: ''; transform: rotate(-24deg); }
.tape { position: absolute; top: -9rpx; left: 18rpx; width: 46rpx; height: 26rpx; background: rgba(231,201,157,.62); transform: rotate(6deg); }
.title { color: var(--ink); font-size: 38rpx; font-weight: 900; letter-spacing: 2rpx; }
.doodle { position: absolute; right: 22rpx; color: var(--brand); font-size: 28rpx; }
.header-weather { position: absolute; z-index: 2; left: 18rpx; display: flex; align-items: center; justify-content: center; width: 176rpx; height: 54rpx; padding: 0 10rpx; border: 1rpx solid #e5d0b1; background: rgba(255,250,238,.96); box-shadow: 0 3rpx 8rpx rgba(100,72,40,.09); transform: rotate(-.7deg); }
.header-weather::before { position: absolute; top: -6rpx; left: 38rpx; width: 49rpx; height: 14rpx; background: rgba(238,201,152,.48); content: ''; }
.header-weather-icon { flex: 0 0 auto; margin-right: 7rpx; font-size: 28rpx; }
.header-weather-copy { overflow: hidden; color: var(--ink); font-size: 20rpx; font-weight: 800; letter-spacing: 0; text-overflow: ellipsis; white-space: nowrap; }
.back-button { position: absolute; left: 28rpx; display: flex; align-items: center; justify-content: center; width: 52rpx; height: 52rpx; color: var(--ink); font-size: 52rpx; font-weight: 300; line-height: 1; }
.dark { background: rgba(248,240,223,.96); }
.dark .title, .dark .back-button { color: var(--ink); }
.compact .title-row { min-height: 34rpx; }

@media (max-width: 350px) {
  .header-weather { left: 12rpx; width: 160rpx; padding: 0 7rpx; }
  .header-weather-icon { margin-right: 4rpx; font-size: 25rpx; }
  .header-weather-copy { font-size: 19rpx; }
}
</style>
