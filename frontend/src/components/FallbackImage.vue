<script setup lang="ts">
import { ref, watch } from 'vue'
import { STORE_IMAGE_FALLBACK } from '../utils/store'
import { getAccessToken } from '../auth/token'
import { env } from '../config/env'

declare const wx: { env: { USER_DATA_PATH: string } }

const imageSourceCache = new Map<string, string>()
const pendingDownloads = new Map<string, Promise<string>>()
const DOWNLOAD_TIMEOUT = 15000

function downloadImage(source: string): Promise<string> {
  const cached = imageSourceCache.get(source)
  if (cached) return Promise.resolve(cached)

  const pending = pendingDownloads.get(source)
  if (pending) return pending

  const task = new Promise<string>((resolve, reject) => {
    const extension = source.match(/\.(jpe?g|png|gif|webp)(?:[?#]|$)/i)?.[1]?.toLowerCase() || 'jpg'
    let hash = 2166136261
    for (let index = 0; index < source.length; index += 1) {
      hash ^= source.charCodeAt(index)
      hash = Math.imul(hash, 16777619)
    }
    const filePath = `${wx.env.USER_DATA_PATH}/store-image-${(hash >>> 0).toString(16)}.${extension}`

    const accessToken = getAccessToken()
    uni.request({
      url: source,
      method: 'GET',
      timeout: DOWNLOAD_TIMEOUT,
      responseType: 'arraybuffer',
      header: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      success: (response) => {
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`图片请求失败，HTTP 状态码：${response.statusCode}`))
          return
        }

        const data = response.data as ArrayBuffer
        if (!data || typeof data.byteLength !== 'number' || data.byteLength === 0) {
          reject(new Error('图片请求返回了空内容'))
          return
        }

        uni.getFileSystemManager().writeFile({
          filePath,
          data,
          success: () => {
            imageSourceCache.set(source, filePath)
            if (import.meta.env.DEV) console.info('[店铺图片] 已写入本地缓存', filePath)
            resolve(filePath)
          },
          fail: (failure) => reject(new Error(failure.errMsg || '图片写入本地文件失败')),
        })
      },
      fail: (failure) => reject(new Error(failure.errMsg || '图片请求失败')),
      complete: () => pendingDownloads.delete(source),
    })
  })

  pendingDownloads.set(source, task)
  return task
}

async function resolveImageSource(source: string): Promise<string> {
  if (source.startsWith('/api/v1')) {
    const absoluteSource = `${env.apiBaseUrl}${source.slice('/api/v1'.length)}`
    // #ifdef MP-WEIXIN
    return downloadImage(absoluteSource)
    // #endif
    return absoluteSource
  }
  // 微信开发版的 image 组件可能拒绝 HTTP 网络图片，先下载为临时文件再渲染。
  // #ifdef MP-WEIXIN
  if (/^http:\/\//i.test(source)) return downloadImage(source)
  // #endif

  return source
}

const props = withDefaults(defineProps<{ src?: string | null; fallback?: string; mode?: string }>(), {
  fallback: STORE_IMAGE_FALLBACK,
  mode: 'aspectFill',
})
const emit = defineEmits<{
  resolved: [source: string]
  tap: []
}>()
const currentSource = ref('')
const failed = ref(false)
let sourceVersion = 0

watch(() => props.src, async (value) => {
  const version = ++sourceVersion
  const source = value || props.fallback
  failed.value = false
  currentSource.value = ''

  try {
    const resolvedSource = await resolveImageSource(source)
    if (version === sourceVersion) {
      currentSource.value = resolvedSource
      emit('resolved', resolvedSource)
    }
  } catch (error) {
    if (version !== sourceVersion) return
    failed.value = true
    console.warn('[店铺图片] 加载失败', source, error)
  }
}, { immediate: true })

function handleError() {
  failed.value = true
  console.warn('[店铺图片] image 组件渲染失败', props.src)
}

function handleLoad() {
  if (import.meta.env.DEV) console.info('[店铺图片] 渲染成功', props.src)
}

function handleTap() {
  emit('tap')
}
</script>

<template>
  <view class="fallback-image" @tap="handleTap">
    <image v-if="currentSource && !failed" class="fallback-image__content" :src="currentSource" :mode="mode" @load="handleLoad" @error="handleError" />
    <view v-else class="fallback-image__state">
      <text>{{ failed ? '图片暂不可用' : '图片加载中…' }}</text>
    </view>
  </view>
</template>

<style>
:host { display: block; }
.fallback-image { display: block; width: 100%; height: 100%; overflow: hidden; }
.fallback-image__content { display: block; width: 100%; height: 100%; }
.fallback-image__state { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; background: #f4ecdf; color: #9a856f; font-size: 20rpx; }
</style>
