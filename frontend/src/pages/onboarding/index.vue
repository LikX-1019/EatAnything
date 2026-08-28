<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import { ApiClientError } from '../../api/types'
import { updateProfile, uploadAvatar, type ProfileUpdate } from '../../api/users'
import { useUserStore } from '../../stores/useUserStore'

const userStore = useUserStore()
const statusBarHeight = uni.getSystemInfoSync().statusBarHeight || 24
const step = ref<1 | 2>(1)
const avatarTempPath = ref('')
const nickname = ref('')
const slogan = ref('')
const avatarUploading = ref(false)
const avatarError = ref('')
const savingProfile = ref(false)
const savingError = ref('')
const loadingSchools = ref(false)
const schoolsError = ref('')
const selectingSchoolId = ref<string | null>(null)

async function uploadChosenAvatar(path: string) {
  avatarUploading.value = true
  avatarError.value = ''
  try {
    await uploadAvatar(path)
    await userStore.refreshProfile()
    avatarTempPath.value = ''
    uni.showToast({ title: '头像已更新', icon: 'success' })
  } catch (error) {
    avatarError.value = error instanceof ApiClientError ? error.message : '头像上传失败，请检查网络后重试'
  } finally {
    avatarUploading.value = false
  }
}

function onChooseAvatar(event: unknown) {
  const detail = (event as { detail?: { avatarUrl?: string } }).detail
  if (detail?.avatarUrl) void uploadChosenAvatar(detail.avatarUrl)
}

function chooseAvatarFromAlbum() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['album'],
    success: (result) => {
      const path = result.tempFilePaths[0]
      if (path) void uploadChosenAvatar(path)
    },
  })
}

async function loadSchools() {
  loadingSchools.value = true
  schoolsError.value = ''
  try {
    await userStore.initialize()
    if (!userStore.schools.length) {
      await userStore.loadSchools()
    }
  } catch (error) {
    schoolsError.value = error instanceof ApiClientError ? error.message : '学校列表加载失败，请检查网络后重试'
  } finally {
    loadingSchools.value = false
  }
}

function enterSchoolStep() {
  step.value = 2
  void loadSchools()
}

async function saveProfileAndNext() {
  savingProfile.value = true
  savingError.value = ''
  try {
    const updates: ProfileUpdate = {}
    if (nickname.value.trim()) updates.nickname = nickname.value.trim()
    if (slogan.value.trim()) updates.slogan = slogan.value.trim()
    if (Object.keys(updates).length) {
      const next = await updateProfile(updates)
      userStore.profile = next
    }
    enterSchoolStep()
  } catch (error) {
    savingError.value = error instanceof ApiClientError ? error.message : '资料保存失败，请检查网络后重试'
  } finally {
    savingProfile.value = false
  }
}

function skipProfile() {
  enterSchoolStep()
}

function dismissOnboarding() {
  uni.setStorageSync('onboarding_dismissed', '1')
  uni.reLaunch({ url: '/pages/home/index' })
}

async function selectSchool(id: string) {
  if (selectingSchoolId.value) return
  selectingSchoolId.value = id
  try {
    await userStore.selectSchool(id)
    uni.removeStorageSync('onboarding_dismissed')
    uni.reLaunch({ url: '/pages/home/index' })
  } catch (error) {
    uni.showToast({ title: error instanceof ApiClientError ? error.message : '学校绑定失败', icon: 'none' })
  } finally {
    selectingSchoolId.value = null
  }
}

function schoolDescription(school: { city?: string | null; district?: string | null; address?: string | null }): string {
  const location = [school.city, school.district].filter(Boolean).join(' · ')
  return location || school.address || '暂无地址信息'
}

onShow(() => {
  if (step.value === 2 && !userStore.schools.length) void loadSchools()
})
</script>

<template>
  <view class="page-shell onboarding-page">
    <view class="onboarding-header" :style="{ paddingTop: `${statusBarHeight}px` }">
      <view class="header-bar">
        <view class="back-button" @tap="dismissOnboarding">‹</view>
        <text class="header-title">欢迎使用校园吃什么</text>
        <view class="back-button placeholder" />
      </view>
      <view class="step-bar">
        <text class="step-item" :class="{ active: step === 1 }">1 完善资料</text>
        <text class="step-arrow">→</text>
        <text class="step-item" :class="{ active: step === 2 }">2 选择学校</text>
      </view>
    </view>

    <view v-if="step === 1" class="step-panel">
      <view class="panel-title">你好，先认识一下吧</view>
      <view class="panel-note">微信会自动填充头像和昵称，也可以跳过</view>
      <!-- #ifdef MP-WEIXIN -->
      <view class="avatar-row">
        <image v-if="avatarTempPath || userStore.profile?.avatarUrl" class="avatar-preview" :src="avatarTempPath || userStore.profile?.avatarUrl || ''" mode="aspectFill" />
        <view v-else class="avatar-preview placeholder">👩🏻‍🍳</view>
        <view class="avatar-actions">
          <button class="avatar-button" open-type="chooseAvatar" :disabled="avatarUploading" @chooseavatar="onChooseAvatar">{{ avatarUploading ? '上传中…' : '选择微信头像' }}</button>
          <button class="avatar-button album-button" :disabled="avatarUploading" @tap="chooseAvatarFromAlbum">从相册选择</button>
        </view>
      </view>
      <!-- #endif -->
      <view class="form-row">
        <text class="form-label">昵称</text>
        <input v-model="nickname" type="nickname" class="form-input" maxlength="80" placeholder="微信昵称将自动填充" placeholder-class="form-placeholder" />
      </view>
      <view class="form-row">
        <text class="form-label">签名</text>
        <input v-model="slogan" class="form-input" maxlength="255" placeholder="一句话介绍自己（可选）" placeholder-class="form-placeholder" />
      </view>
      <view v-if="avatarError" class="form-error">{{ avatarError }}</view>
      <view v-if="savingError" class="form-error">{{ savingError }}</view>
      <button class="primary-button" :disabled="savingProfile" @tap="saveProfileAndNext">{{ savingProfile ? '保存中…' : '下一步' }}</button>
      <button class="skip-button" :disabled="savingProfile" @tap="skipProfile">跳过，直接选学校</button>
    </view>

    <view v-else class="step-panel">
      <view class="panel-title">选择你的学校</view>
      <view class="panel-note">选择后即可开始使用校园吃什么</view>
      <view v-if="loadingSchools" class="page-state">正在加载学校…</view>
      <view v-else-if="schoolsError" class="page-state">
        <text>{{ schoolsError }}</text>
        <button class="retry-button" @tap="loadSchools()">重新加载</button>
      </view>
      <template v-else>
        <view v-for="school in userStore.schools" :key="school.id" class="school-option" @tap="selectSchool(school.id)">
          <view class="school-copy">
            <text class="school-name">{{ school.name }}</text>
            <text class="school-areas">{{ schoolDescription(school) }}</text>
          </view>
          <text class="school-mark">{{ selectingSchoolId === school.id ? '…' : '›' }}</text>
        </view>
        <view v-if="!userStore.schools.length" class="page-state">暂无可选学校</view>
      </template>
      <button class="back-step-button" @tap="step = 1">‹ 上一步</button>
    </view>
  </view>
</template>

<style scoped>
.onboarding-page { min-height: 100vh; background: var(--page); }
.onboarding-header { position: sticky; top: 0; z-index: 10; padding-bottom: 12rpx; background: var(--page); }
.header-bar { display: flex; align-items: center; justify-content: space-between; height: 88rpx; padding: 0 24rpx; }
.back-button { display: flex; align-items: center; justify-content: center; width: 64rpx; height: 64rpx; color: var(--ink); font-size: 52rpx; font-weight: 300; line-height: 1; }
.back-button.placeholder { visibility: hidden; }
.header-title { font-size: 32rpx; font-weight: 900; }
.step-bar { display: flex; align-items: center; justify-content: center; gap: 18rpx; padding: 6rpx 0 16rpx; }
.step-item { font-size: 25rpx; color: var(--muted); font-weight: 800; }
.step-item.active { color: var(--brand); }
.step-arrow { color: var(--line); }
.step-panel { margin: 0 30rpx 40rpx; padding: 30rpx 26rpx; border: 1rpx solid #e1c8a5; border-radius: 5rpx 12rpx 7rpx 9rpx; background: #fffaf0; box-shadow: var(--paper-shadow); }
.panel-title { font-size: 38rpx; font-weight: 900; }
.panel-note { margin-top: 10rpx; color: var(--muted); font-size: 24rpx; }
.avatar-row { display: flex; align-items: center; gap: 26rpx; margin-top: 30rpx; }
.avatar-preview { display: flex; align-items: center; justify-content: center; width: 128rpx; height: 128rpx; border: 5rpx solid #fff; border-radius: 50%; background: #f7dfc9; font-size: 56rpx; box-shadow: 0 0 0 2rpx #e7c7ad; }
.avatar-button { padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
.avatar-actions { display: flex; flex-direction: column; gap: 14rpx; }
.album-button { background: var(--green); box-shadow: 0 4rpx 0 #5f8857; }
.form-row { display: flex; align-items: center; margin-top: 26rpx; padding: 0 20rpx; height: 84rpx; border: 1rpx dashed #dfccb0; border-radius: 10rpx; background: #fffdf6; }
.form-label { flex: 0 0 96rpx; color: var(--brand-deep); font-size: 26rpx; font-weight: 800; }
.form-input { flex: 1; height: 78rpx; font-size: 27rpx; }
.form-placeholder { color: #b7a48f; }
.form-error { margin-top: 18rpx; color: #c0392b; font-size: 23rpx; }
.primary-button { width: 100%; height: 82rpx; margin-top: 34rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 29rpx; font-weight: 900; box-shadow: 0 5rpx 0 #c75f4b; }
.primary-button[disabled] { opacity: .55; }
.skip-button { width: 100%; height: 72rpx; margin-top: 14rpx; color: var(--muted); font-size: 25rpx; }
.back-step-button { width: 100%; height: 72rpx; margin-top: 16rpx; color: var(--muted); font-size: 25rpx; }
.page-state { padding: 60rpx 20rpx; color: var(--muted); text-align: center; font-size: 26rpx; }
.retry-button { margin: 22rpx auto 0; padding: 0 26rpx; height: 68rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 25rpx; }
.school-option { display: flex; align-items: center; justify-content: space-between; min-height: 92rpx; padding: 16rpx 4rpx; border-bottom: 1rpx solid var(--line); }
.school-copy { min-width: 0; flex: 1; }
.school-name, .school-areas { display: block; }
.school-name { font-size: 28rpx; font-weight: 800; }
.school-areas { margin-top: 7rpx; color: var(--muted); font-size: 21rpx; }
.school-mark { color: var(--brand); font-size: 34rpx; }
</style>
