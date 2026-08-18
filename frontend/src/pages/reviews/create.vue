<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../../stores/useAppStore'
import PageHeader from '../../components/PageHeader.vue'

const appStore = useAppStore()
const storeId = ref(appStore.activeAreaStores[0]?.id || 0)
const rating = ref(5)
const content = ref('')
const selectedStore = computed(() => appStore.findStore(storeId.value))
const selectableStores = computed(() => appStore.activeSchoolStores)

function submit() {
  if (!storeId.value) return uni.showToast({ title: '请先选择店铺', icon: 'none' })
  if (!content.value.trim()) return uni.showToast({ title: '写点真实感受吧', icon: 'none' })
  appStore.addReview(storeId.value, rating.value, content.value.trim())
  uni.showToast({ title: '评价已提交', icon: 'success' })
  setTimeout(() => uni.navigateBack(), 500)
}
</script>

<template>
  <view class="page-shell create-page" :class="appStore.fontClass">
    <PageHeader title="评价店铺" back />
    <view class="page-pad">
      <text class="label">评价哪家店？</text>
      <scroll-view scroll-x class="store-picker" :show-scrollbar="false">
        <view v-for="store in selectableStores" :key="store.id" class="store-chip" :class="{ active: store.id === storeId }" @tap="storeId = store.id">
          <image :src="store.image" mode="aspectFill" /><text>{{ store.name }}</text>
        </view>
      </scroll-view>
      <text class="label rating-label">打个分</text>
      <view class="rating-row"><text v-for="item in 5" :key="item" class="star" :class="{ active: item <= rating }" @tap="rating = item">★</text><text class="rating-copy">{{ rating }} 分</text></view>
      <text class="label">说说感受</text>
      <textarea v-model="content" class="review-input" maxlength="200" placeholder="味道、价格、位置都可以写下来" placeholder-class="review-placeholder" />
      <text class="counter">{{ content.length }}/200</text>
      <button class="submit-button" @tap="submit">提交评价</button>
      <text v-if="selectedStore" class="selected-store">当前：{{ selectedStore.name }} · {{ appStore.findArea(selectedStore)?.name }}</text>
    </view>
  </view>
</template>

<style scoped>
.create-page { background: var(--page); }
.page-pad { padding: 30rpx; }
.label { display: block; margin-bottom: 14rpx; color: var(--ink); font-size: 28rpx; font-weight: 800; }
.rating-label { margin-top: 30rpx; }
.store-picker { width: 100%; white-space: nowrap; }
.store-chip { display: inline-flex; align-items: center; width: 260rpx; margin-right: 14rpx; padding: 12rpx; border: 1rpx solid transparent; border-radius: 12rpx; background: #fff; }
.store-chip.active { border-color: var(--brand); background: #f2faf5; }
.store-chip image { width: 62rpx; height: 62rpx; border-radius: 10rpx; }
.store-chip text { max-width: 170rpx; margin-left: 12rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 23rpx; }
.rating-row { display: flex; align-items: center; gap: 12rpx; margin-bottom: 30rpx; }
.star { color: #d7dfda; font-size: 54rpx; }
.star.active { color: var(--amber); }
.rating-copy { margin-left: 8rpx; color: var(--muted); font-size: 24rpx; }
.review-input { width: 100%; min-height: 260rpx; padding: 22rpx; border-radius: 12rpx; background: #fff; font-size: 26rpx; line-height: 1.6; }
.review-placeholder { color: #9aa9a1; }
.counter { display: block; margin-top: 8rpx; color: var(--muted); font-size: 21rpx; text-align: right; }
.submit-button { width: 100%; height: 84rpx; margin-top: 28rpx; border-radius: 12rpx; background: var(--brand); color: #fff; font-size: 28rpx; font-weight: 800; }
.selected-store { display: block; margin-top: 20rpx; color: var(--muted); font-size: 22rpx; text-align: center; }
</style>
