<script setup lang="ts">
withDefaults(defineProps<{ title?: string; description?: string }>(), {
  title: '这里还没有内容',
  description: '去发现一家喜欢的店铺吧'
})
</script>

<template>
  <view class="empty-state">
    <view class="empty-icon">🍽</view>
    <text class="empty-title">{{ title }}</text>
    <text class="empty-description">{{ description }}</text>
  </view>
</template>

<style scoped>
.empty-state { display: flex; align-items: center; flex-direction: column; justify-content: center; min-height: 480rpx; padding: 64rpx 32rpx; text-align: center; }
.empty-icon { position: relative; display: flex; align-items: center; justify-content: center; width: 112rpx; height: 112rpx; border: 2rpx dashed #d59380; border-radius: 12rpx 20rpx 13rpx 18rpx; background: #fff4df; font-size: 58rpx; box-shadow: var(--paper-shadow); transform: rotate(-3deg); }
.empty-title { margin-top: 28rpx; font-size: 31rpx; font-weight: 700; }
.empty-description { margin-top: 12rpx; color: var(--muted); font-size: 25rpx; }
</style>
