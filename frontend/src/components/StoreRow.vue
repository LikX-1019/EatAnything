<script setup lang="ts">
import type { StoreItem } from '../types'
defineProps<{ store: StoreItem }>()
defineEmits<{ (event: 'press', store: StoreItem): void }>()
</script>

<template>
  <view class="store-row" hover-class="tap-active" @tap="$emit('press', store)">
    <text class="row-tape" />
    <image class="store-image" :src="store.image" mode="aspectFill" />
    <view class="store-info">
      <view class="name-line">
        <text class="store-name single-line">{{ store.name }}</text>
        <text v-if="store.favorite" class="favorite">♥</text>
      </view>
      <text class="category">{{ store.category }}</text>
      <view class="meta-line">
        <text class="address single-line">{{ store.address }}</text>
        <text class="score">★ {{ store.score.toFixed(1) }}</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.store-row { position: relative; display: flex; align-items: center; width: 100%; min-height: 190rpx; margin: 18rpx 0; padding: 18rpx; border: 1rpx solid #e8d8be; border-radius: 8rpx 18rpx 10rpx 16rpx; background-color: rgba(255,253,246,.92); background-image: linear-gradient(rgba(218,191,155,.13) 1rpx, transparent 1rpx), linear-gradient(90deg, rgba(218,191,155,.11) 1rpx, transparent 1rpx); background-size: 28rpx 28rpx; box-shadow: var(--paper-shadow); transform: rotate(.15deg); }
.row-tape { position: absolute; z-index: 2; top: -10rpx; left: 80rpx; width: 76rpx; height: 24rpx; background: rgba(238,177,161,.55); transform: rotate(-4deg); }
.store-image { flex: 0 0 auto; width: 156rpx; height: 146rpx; padding: 6rpx; border: 1rpx solid #decab0; border-radius: 14rpx 9rpx 15rpx 8rpx; background: #fff; box-shadow: 0 4rpx 8rpx rgba(105,73,39,.13); }
.store-info { min-width: 0; flex: 1; padding-left: 24rpx; }
.name-line, .meta-line { display: flex; align-items: center; }
.store-name { max-width: 420rpx; font-size: 35rpx; font-weight: 800; }
.favorite { margin-left: 10rpx; color: var(--coral); font-size: 28rpx; }
.category { display: block; margin-top: 14rpx; color: #765f4e; font-size: 28rpx; }
.meta-line { justify-content: space-between; gap: 16rpx; margin-top: 15rpx; color: var(--muted); font-size: 27rpx; }
.address { min-width: 0; flex: 1; }
.score { flex: 0 0 auto; color: var(--amber); font-weight: 800; }
</style>
