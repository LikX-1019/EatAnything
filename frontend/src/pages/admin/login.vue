<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { adminLogin, hasAdminSession } from '../../api/admin'
import { ApiClientError } from '../../api/types'

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

onLoad(() => { if (hasAdminSession()) uni.redirectTo({ url: '/pages/admin/stores' }) })
async function submit() {
  if (!username.value.trim() || !password.value) { errorMessage.value = '请输入管理员账号和密码'; return }
  loading.value = true; errorMessage.value = ''
  try { await adminLogin(username.value.trim(), password.value); uni.redirectTo({ url: '/pages/admin/stores' }) }
  catch (error) { errorMessage.value = error instanceof ApiClientError ? error.message : '登录失败，请重试' }
  finally { loading.value = false }
}
</script>

<template>
  <view class="admin-page"><view class="panel"><text class="title">店铺管理后台</text><text class="subtitle">管理员登录</text>
    <input v-model="username" class="field" placeholder="管理员账号" autocomplete="username" />
    <input v-model="password" class="field" password placeholder="密码" autocomplete="current-password" />
    <text v-if="errorMessage" class="error">{{ errorMessage }}</text>
    <button class="primary" :disabled="loading" @tap="submit">{{ loading ? '登录中…' : '登录' }}</button>
  </view></view>
</template>

<style scoped>
.admin-page { min-height: 100vh; padding: 80rpx 30rpx; background: #f4f6f8; }.panel { max-width: 680rpx; margin: 0 auto; padding: 42rpx 34rpx; border-radius: 18rpx; background: #fff; box-shadow: 0 8rpx 28rpx rgba(0,0,0,.06); }.title,.subtitle,.error { display: block; }.title { color: #203040; font-size: 40rpx; font-weight: 800; }.subtitle { margin-top: 12rpx; color: #718090; font-size: 26rpx; }.field { height: 84rpx; margin-top: 24rpx; padding: 0 20rpx; border: 1rpx solid #d6dde5; border-radius: 10rpx; background: #fafbfd; }.error { margin-top: 16rpx; color: #c53d3d; font-size: 24rpx; }.primary { margin-top: 28rpx; border-radius: 10rpx; background: #2f6fed; color: #fff; }
</style>
