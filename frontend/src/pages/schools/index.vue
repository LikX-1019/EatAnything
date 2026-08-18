<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../../stores/useAppStore'
import PageHeader from '../../components/PageHeader.vue'

const appStore = useAppStore()
const keyword = ref('')
const schools = computed(() => appStore.schools.filter((school) => !keyword.value.trim() || school.name.includes(keyword.value.trim())))

function selectSchool(id: string) {
  appStore.selectSchool(id)
  uni.navigateBack()
}

</script>

<template>
  <view class="page-shell schools-page" :class="appStore.fontClass">
    <PageHeader title="选择学校" back />
    <view class="page-pad">
      <view class="search-box"><text class="search-icon">⌕</text><input v-model="keyword" class="search-input" placeholder="搜索学校名称" placeholder-class="search-placeholder" /></view>
      <text class="list-label">当前学校</text>
      <view v-for="school in schools" :key="school.id" class="school-option" :class="{ active: school.id === appStore.selectedSchoolId }" @tap="selectSchool(school.id)">
        <view class="school-copy"><text class="school-name">{{ school.name }}</text><text class="school-areas">{{ school.areas.map((area) => area.name).join(' · ') }}</text></view>
        <text class="school-mark">{{ school.id === appStore.selectedSchoolId ? '⊙' : '›' }}</text>
      </view>
    </view>
  </view>
</template>

<style scoped>
.schools-page { background: var(--page); }
.page-pad { padding: 0 30rpx; }
.search-box { display: flex; align-items: center; height: 82rpx; padding: 0 22rpx; border: 1rpx solid var(--line); border-radius: 10rpx; background: #fff; }
.search-icon { margin-right: 12rpx; color: var(--muted); font-size: 40rpx; }
.search-input { flex: 1; height: 76rpx; font-size: 25rpx; }
.search-placeholder { color: #9aa9a1; }
.list-label { display: block; margin-top: 24rpx; color: var(--muted); font-size: 22rpx; font-weight: 700; }
.school-option { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; padding: 16rpx 0; border-bottom: 1rpx solid var(--line); }
.school-copy { min-width: 0; flex: 1; }
.school-name, .school-areas { display: block; }
.school-name { font-size: 28rpx; font-weight: 800; }
.school-areas { margin-top: 7rpx; color: var(--muted); font-size: 21rpx; }
.school-mark { color: var(--brand); font-size: 34rpx; }
</style>
