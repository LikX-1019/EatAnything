<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import { ApiClientError } from '../../api/types'
import PageHeader from '../../components/PageHeader.vue'
import FallbackImage from '../../components/FallbackImage.vue'
// #ifndef MP-WEIXIN
import StickerTabBar from '../../components/StickerTabBar.vue'
// #endif
import { useAppStore } from '../../stores/useAppStore'
import { useUserStore } from '../../stores/useUserStore'
import { useMessageStore } from '../../stores/useMessageStore'
import { storeImageUrl, storeScoreLabel } from '../../utils/store'
import { syncTabBarSelected } from '../../utils/tabbar'

const appStore = useAppStore()
const userStore = useUserStore()
const messageStore = useMessageStore()
const isDrawing = ref(false)
const isCheckingIn = ref(false)
const loading = ref(true)
const loadError = ref('')
let onboardingRedirected = false
const rollingName = ref('准备好了吗？')
const DRAW_DURATION_MS = 1000
const currentPickImageSource = ref('')
let shuffleTimer: ReturnType<typeof setInterval> | null = null
let finishTimer: ReturnType<typeof setTimeout> | null = null
const currentPickCheckIn = computed(() => appStore.currentPick ? appStore.latestCheckInForStore(appStore.currentPick.id) : undefined)
function showError(error: unknown, fallback: string) {
  uni.showToast({ title: error instanceof ApiClientError ? error.message : fallback, icon: 'none' })
}

async function loadHome(refresh = false) {
  loading.value = !refresh
  loadError.value = ''
  try {
    if (refresh) await appStore.refresh()
    else await appStore.initialize()
    await messageStore.refreshAnnouncements()
    if (!userStore.profile?.schoolId && !onboardingRedirected) {
      onboardingRedirected = true
      uni.redirectTo({ url: '/pages/onboarding/index' })
      return
    }
  } catch (error) {
    loadError.value = error instanceof ApiClientError ? error.message : '首页加载失败，请重试'
    showError(error, '核心数据加载失败')
  } finally {
    loading.value = false
    if (refresh) uni.stopPullDownRefresh()
  }
}
onShow(() => {
  syncTabBarSelected(0)
  void loadHome()
})
onPullDownRefresh(() => { void loadHome(true) })

function chooseSchool() { uni.navigateTo({ url: '/pages/schools/index' }) }
function openAnnouncement(id:string){uni.navigateTo({url:`/pages/messages/detail?id=${id}`})}
function chooseArea(id: string) { appStore.selectArea(id) }
async function drawStore() {
  if (isDrawing.value || appStore.isPickLocked) return
  if (!userStore.profile?.schoolId) return uni.showToast({ title: '请先选择学校', icon: 'none' })
  const pool = appStore.activeSchoolStores
  if (!pool.length) return uni.showToast({ title: '当前学校暂无店铺', icon: 'none' })
  rollingName.value = pool[0].name
  isDrawing.value = true
  let cursor = 1
  shuffleTimer = setInterval(() => { rollingName.value = pool[cursor++ % pool.length].name }, 90)
  const animation = new Promise<void>((resolve) => {
    finishTimer = setTimeout(resolve, DRAW_DURATION_MS)
  })
  try {
    const [next] = await Promise.all([appStore.drawRandomStore(), animation])
    rollingName.value = next.name
  } catch (error) {
    showError(error, '随机抽取失败')
  } finally {
    if (shuffleTimer) clearInterval(shuffleTimer)
    if (finishTimer) clearTimeout(finishTimer)
    shuffleTimer = null
    finishTimer = null
    isDrawing.value = false
  }
}
function replaceCurrentPick() { void drawStore() }
async function togglePickLock() {
  if (appStore.isPickLocked) {
    if (appStore.unlockCurrentPick()) {
      uni.showToast({ title: '已取消锁定，可以重新抽取', icon: 'none' })
    } else {
      uni.showToast({ title: '已完成打卡，不能取消锁定', icon: 'none' })
    }
    return
  }
  if (!appStore.currentPick) return
  try {
    await appStore.confirmStoreChoice(appStore.currentPick.id)
    if (appStore.lockCurrentPick()) uni.showToast({ title: '已锁定这家店', icon: 'none' })
  } catch (error) {
    showError(error, '记录选择失败')
  }
}
async function toggleFavorite() {
  if (!appStore.currentPick) return
  try {
    const active = await appStore.toggleFavorite(appStore.currentPick.id)
    uni.showToast({ title: active ? '已加入收藏' : '已取消收藏', icon: 'none' })
  } catch (error) {
    showError(error, '收藏操作失败')
  }
}
function chooseCheckInImage(): Promise<string | null> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (result) => resolve(result.tempFilePaths[0] || null),
      fail: (error) => {
        if (error.errMsg?.toLowerCase().includes('cancel')) resolve(null)
        else reject(new ApiClientError(error.errMsg || '选择图片失败', { code: 'IMAGE_PICK_FAILED', cause: error }))
      },
    })
  })
}
async function checkIn() {
  if (!appStore.currentPick || !appStore.isPickLocked || isCheckingIn.value) return
  try {
    const filePath = await chooseCheckInImage()
    if (!filePath) return
    isCheckingIn.value = true
    await appStore.createCheckIn(appStore.currentPick.id, filePath)
    promptReviewAfterCheckIn()
  } catch (error) {
    showError(error, '打卡失败，请重试')
  } finally {
    isCheckingIn.value = false
  }
}
function promptReviewAfterCheckIn() {
  const store = appStore.currentPick
  if (!store) return
  uni.showModal({
    title: '打卡成功',
    content: `已打卡「${store.name}」，是否立即评价这家店？`,
    confirmText: '去评价',
    cancelText: '稍后再说',
    success: ({ confirm }) => {
      if (confirm) uni.navigateTo({ url: `/pages/reviews/create?storeId=${encodeURIComponent(store.id)}` })
    },
  })
}
function formatCheckInTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
function previewCurrentPickImage() {
  if (!appStore.currentPick) return
  const source = currentPickImageSource.value || currentPickCheckIn.value?.photoUrl || storeImageUrl(appStore.currentPick)
  uni.previewImage({ urls: [source] })
}
function chooseCheckInAction(): Promise<string | null> {
  return chooseCheckInImage()
}
async function replaceCurrentPickCheckIn() {
  const checkIn = currentPickCheckIn.value
  if (!checkIn || !appStore.currentPick || isCheckingIn.value) return
  try {
    const filePath = await chooseCheckInAction()
    if (!filePath) return
    isCheckingIn.value = true
    await appStore.updateCheckIn(checkIn.id, filePath)
    currentPickImageSource.value = ''
    uni.showToast({ title: '打卡图片已更新', icon: 'success' })
  } catch (error) {
    showError(error, '修改打卡图片失败')
  } finally {
    isCheckingIn.value = false
  }
}
async function addCurrentPickCheckIn() {
  if (!appStore.currentPick || isCheckingIn.value) return
  try {
    const filePath = await chooseCheckInAction()
    if (!filePath) return
    isCheckingIn.value = true
    await appStore.createCheckIn(appStore.currentPick.id, filePath)
    uni.showToast({ title: '已添加新的打卡记录', icon: 'success' })
  } catch (error) {
    showError(error, '添加打卡记录失败')
  } finally {
    isCheckingIn.value = false
  }
}
function openCurrentPickImage() {
  if (!currentPickCheckIn.value) return previewCurrentPickImage()
  uni.showActionSheet({
    itemList: ['查看大图', '修改图片', '添加打卡记录'],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) previewCurrentPickImage()
      else if (tapIndex === 1) void replaceCurrentPickCheckIn()
      else if (tapIndex === 2) void addCurrentPickCheckIn()
    },
  })
}
function setCurrentPickImageSource(source: string) { currentPickImageSource.value = source }
onUnmounted(() => { if (shuffleTimer) clearInterval(shuffleTimer); if (finishTimer) clearTimeout(finishTimer) })
</script>

<template>
  <view class="page-shell home-page" :class="appStore.fontClass">
    <PageHeader title="今天吃什么" weather />
    <view class="content-width home-content">
      <view v-if="loading" class="page-state">正在加载首页…</view>
      <view v-else-if="loadError" class="page-state"><text>{{ loadError }}</text><button class="retry-button" @tap="loadHome()">重新加载</button></view>
      <template v-else>
      <view class="scope-card">
        <button class="school-button" hover-class="tap-active" @tap="chooseSchool">📌 {{ userStore.profile?.school?.name || '选择学校' }} <text class="chevron">⌄</text></button>
        <scroll-view scroll-x class="area-tabs" :show-scrollbar="false">
          <view v-for="area in appStore.activeAreas" :key="area.id" class="area-tab" :class="{ active: area.id === appStore.selectedAreaId }" @tap="chooseArea(area.id)">{{ area.name }}</view>
        </scroll-view>
        <text class="random-scope-note">区域用于浏览筛选；随机结果由后端店铺池生成</text>
      </view>
      <swiper v-if="messageStore.announcements.length" class="announcement-swiper" circular autoplay :interval="5000" indicator-dots>
        <swiper-item v-for="notice in messageStore.announcements" :key="notice.id"><view class="announcement-card" :class="{important:notice.priority==='important'}" @tap="openAnnouncement(notice.id)"><text class="announcement-tag">📣 平台公告</text><text class="announcement-title">{{notice.title}}</text><text class="announcement-more">查看详情 ›</text></view></swiper-item>
      </swiper>
      <view class="lucky-stage" :class="{ 'has-result': appStore.currentPick && !isDrawing }">
        <text class="corner-flower">✿</text><text class="corner-star">✦</text>
        <view class="lucky-frame">
          <view class="lucky-paper" :class="{ 'has-result': appStore.currentPick && !isDrawing }">
            <template v-if="!appStore.currentPick && !isDrawing"><text class="sun-mark">☀</text><text class="lucky-label">幸运抽签</text></template>
            <template v-if="appStore.currentPick && !isDrawing">
              <FallbackImage class="picked-image" :src="currentPickCheckIn?.photoUrl || storeImageUrl(appStore.currentPick)" @tap="openCurrentPickImage" @resolved="setCurrentPickImageSource" />
              <view class="picked-copy">
                <text class="picked-name">{{ appStore.currentPick.name }}</text>
                <text class="picked-meta">{{ appStore.currentPick.category }} · ★ {{ storeScoreLabel(appStore.currentPick) }}</text>
                <text class="picked-address">⌖ {{ appStore.currentPick.address }}</text>
                <text v-if="currentPickCheckIn" class="check-in-time">打卡于 {{ formatCheckInTime(currentPickCheckIn.checkedAt) }} · 点击图片可查看或编辑</text>
              </view>
            </template>
            <view v-else-if="isDrawing" class="rolling-state">
              <text class="rolling-name">{{ rollingName }}</text>
              <text class="rolling-copy">好运正在翻页…</text>
            </view>
            <view v-else class="ready-state">
              <text class="ready-icon">🍽️</text>
              <text class="ready-title">今天想吃点什么？</text>
              <text class="ready-copy">拉一下，让好运替你选一家</text>
            </view>
          </view>
        </view>
        <button class="pull-tab" :disabled="isDrawing || appStore.isPickLocked" hover-class="button-active" @tap="appStore.currentPick ? replaceCurrentPick() : drawStore()"><text class="tab-heart">♡</text><text>{{ isDrawing ? '抽签中' : appStore.currentPick ? '再抽一次' : 'PULL' }}</text></button>
        <view class="string" />
      </view>
      <view v-if="appStore.currentPick && !isDrawing" class="result-actions">
        <button class="favorite-button" @tap="toggleFavorite">{{ appStore.currentPick.isFavorite ? '♥ 已收藏' : '♡ 收藏' }}</button>
        <button class="lock-button" :class="{ locked: appStore.isPickLocked }" @tap="togglePickLock">{{ appStore.isPickLocked ? '↶ 取消锁定' : '✓ 就吃这家！' }}</button>
      </view>
      <view v-if="appStore.isPickLocked" class="check-in-row"><text>{{ currentPickCheckIn ? '还可以继续记录这家店的到店照片' : '这顿就这么定啦，到了记得打卡～' }}</text><button :disabled="isCheckingIn" @tap="checkIn">{{ isCheckingIn ? '上传中' : currentPickCheckIn ? '添加打卡' : '到店打卡' }}</button></view>
      <view class="section-heading"><text>探索校园店铺</text><text>{{ appStore.activeArea?.name }} · {{ appStore.activeAreaStores.length }} 家可抽</text></view>
      <view class="activity-placeholder">完成一次打卡后，你的真实足迹会出现在“吃过的店铺”和“历史记录”中。</view>
      </template>
    </view>
    <!-- #ifndef MP-WEIXIN -->
    <StickerTabBar />
    <!-- #endif -->
  </view>
</template>

<style scoped>
.home-page { background: transparent; }
.home-content { position: relative; padding: 18rpx 30rpx 24rpx; overflow: hidden; }
.page-state { display: flex; align-items: center; justify-content: center; min-height: 520rpx; padding: 40rpx; color: var(--muted); font-size: 28rpx; flex-direction: column; text-align: center; }.retry-button { margin-top: 22rpx; padding: 0 26rpx; height: 70rpx; border-radius: 10rpx; background: var(--brand); color: #fff; font-size: 26rpx; }
.scope-card { margin-top: 12rpx; padding: 14rpx 16rpx; border: 1rpx dashed #d5b990; border-radius: 12rpx; background: rgba(255,250,236,.62); }.school-button { display: inline-flex; align-items: center; height: 48rpx; padding: 0; color: var(--brand-deep); font-size: 27rpx; font-weight: 800; }.chevron { margin-left: 4rpx; }.area-tabs { width: 100%; margin-top: 10rpx; white-space: nowrap; }.area-tab { display: inline-flex; align-items: center; height: 56rpx; margin-right: 10rpx; padding: 0 22rpx; border: 1rpx solid #dfc8a5; border-radius: 7rpx 12rpx 8rpx 11rpx; background: #fffaf0; color: #806b56; font-size: 25rpx; }.area-tab.active { border-color: #e38b78; background: #f8d8ce; color: #a85043; font-weight: 800; box-shadow: 0 3rpx 0 #dca092; }
.announcement-swiper{height:160rpx;margin-top:18rpx}.announcement-card{position:relative;height:140rpx;padding:20rpx 24rpx;border:1rpx solid #e1c59f;border-radius:9rpx 15rpx 8rpx 12rpx;background:#fff6dc;box-shadow:var(--paper-shadow)}.announcement-card.important{border-left:8rpx solid var(--brand)}.announcement-tag,.announcement-title{display:block}.announcement-tag{color:var(--brand);font-size:22rpx;font-weight:900}.announcement-title{margin-top:10rpx;overflow:hidden;font-size:30rpx;font-weight:900;text-overflow:ellipsis;white-space:nowrap}.announcement-more{position:absolute;right:22rpx;bottom:14rpx;color:var(--muted);font-size:21rpx}
.random-scope-note { display: block; margin-top: 8rpx; color: var(--muted); font-size: 20rpx; }
.lucky-stage { position: relative; height: 650rpx; margin: 20rpx 16rpx 0; padding: 25rpx 30rpx 68rpx; border: 3rpx solid rgba(220,145,125,.52); border-radius: 20rpx; background: rgba(244,180,165,.32); box-shadow: inset 0 0 0 12rpx rgba(255,255,255,.23); }.lucky-stage::before { position: absolute; top: 12rpx; right: 16rpx; bottom: 12rpx; left: 16rpx; border: 2rpx dashed rgba(195,115,95,.35); border-radius: 16rpx; content: ''; }.corner-flower, .corner-star { position: absolute; z-index: 3; color: var(--brand); font-size: 35rpx; }.corner-flower { top: 16rpx; left: 18rpx; }.corner-star { top: 20rpx; right: 22rpx; color: var(--amber); }
.lucky-frame { position: relative; z-index: 2; padding: 16rpx; background: rgba(255,247,226,.75); box-shadow: var(--paper-shadow); transform: rotate(-1deg); }.lucky-paper { position: relative; display: flex; align-items: center; flex-direction: column; justify-content: flex-start; height: 518rpx; padding: 22rpx 20rpx; overflow: hidden; border: 1rpx solid #d8bd99; background: #fffaf0; box-shadow: inset 0 0 22rpx rgba(157,111,66,.06); }.lucky-paper.has-result { padding: 18rpx 20rpx 10rpx; }.lucky-paper::before, .lucky-paper::after { position: absolute; top: -15rpx; width: 86rpx; height: 30rpx; background: rgba(239,200,145,.5); content: ''; }.lucky-paper::before { left: -26rpx; transform: rotate(-25deg); }.lucky-paper::after { right: -24rpx; transform: rotate(24deg); }.sun-mark { flex: 0 0 auto; color: var(--amber); font-size: 32rpx; }.lucky-label { flex: 0 0 auto; margin-top: 3rpx; font-size: 31rpx; font-weight: 900; letter-spacing: 4rpx; }
.rolling-state, .ready-state { display: flex; align-items: center; flex: 1; flex-direction: column; justify-content: center; width: 100%; min-height: 0; text-align: center; }.rolling-name { display: block; width: 100%; overflow: hidden; color: var(--ink); font-size: 43rpx; font-weight: 900; line-height: 1.35; text-align: center; text-overflow: ellipsis; white-space: nowrap; }.rolling-copy { margin-top: 18rpx; color: var(--muted); font-size: 24rpx; }.ready-icon { font-size: 62rpx; line-height: 1; }.ready-title { margin-top: 20rpx; color: var(--ink); font-size: 34rpx; font-weight: 900; }.ready-copy { margin-top: 13rpx; color: var(--muted); font-size: 24rpx; }
.picked-image { display: block; flex: 1 1 0; width: 100%; min-height: 0; margin-top: 8rpx; padding: 6rpx; overflow: hidden; border: 1rpx solid #dec8a8; background: #fff; box-shadow: 0 6rpx 10rpx rgba(94,67,38,.18); transform: rotate(1.5deg); }.picked-copy { display: flex; flex: 0 0 auto; align-items: center; flex-direction: column; width: 100%; margin-top: 8rpx; padding-bottom: 4rpx; }.picked-name, .picked-meta, .picked-address { display: block; max-width: 100%; overflow: hidden; text-align: center; text-overflow: ellipsis; white-space: nowrap; }.picked-name { font-size: 36rpx; font-weight: 900; }.picked-meta, .picked-address { margin-top: 4rpx; color: var(--muted); font-size: 24rpx; }.check-in-time { display: block; max-width: 100%; margin-top: 5rpx; color: var(--brand); font-size: 21rpx; line-height: 1.35; text-align: center; }
.pull-tab { position: absolute; z-index: 4; right: 72rpx; bottom: -38rpx; display: flex; align-items: center; flex-direction: column; justify-content: center; width: 122rpx; height: 124rpx; border: 1rpx solid #dc9e82; border-radius: 3rpx 3rpx 14rpx 14rpx; background: #f7d7c4; color: #634332; font-size: 24rpx; font-weight: 900; letter-spacing: 2rpx; box-shadow: 0 5rpx 8rpx rgba(104,63,39,.15); transform: rotate(2deg); }.pull-tab::before { position: absolute; top: -9rpx; width: 33rpx; height: 18rpx; border: 2rpx solid #9e7156; border-radius: 50%; content: ''; }.pull-tab[disabled] { opacity: .65; }.tab-heart { font-size: 29rpx; }.string { position: absolute; right: 124rpx; bottom: -82rpx; width: 2rpx; height: 58rpx; background: #8b5c42; transform: rotate(-5deg); }.button-active { transform: translateY(3rpx) rotate(2deg); }
.result-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 16rpx; margin: 72rpx 16rpx 0; }.favorite-button, .lock-button { display: flex; align-items: center; justify-content: center; height: 82rpx; padding: 0 12rpx; border-radius: 10rpx; font-size: 30rpx; font-weight: 900; line-height: 1.2; text-align: center; }.favorite-button { border: 2rpx dashed #df9b8e; background: #fffaf0; color: var(--brand); }.lock-button { background: var(--green); color: #fff; box-shadow: 0 5rpx 0 #5f8857; }.lock-button.locked { border: 2rpx dashed #d98e79; background: #fff5e9; color: #b65e4d; box-shadow: 0 4rpx 0 #e4b29f; }.check-in-row { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; margin: 16rpx; padding: 16rpx 18rpx; border: 1rpx dashed #88aa75; background: #edf4df; color: #53704c; font-size: 24rpx; }.check-in-row button { display: flex; align-items: center; justify-content: center; flex: 0 0 auto; padding: 13rpx 17rpx; border-radius: 8rpx; background: var(--green); color: #fff; font-size: 24rpx; }
.section-heading { display: flex; align-items: center; justify-content: space-between; margin: 76rpx 0 18rpx; font-size: 32rpx; font-weight: 900; }.section-heading > text:first-child { padding: 5rpx 14rpx; background: linear-gradient(transparent 55%, rgba(239,165,137,.45) 55%); }.section-heading text:last-child { color: var(--muted); font-size: 23rpx; font-weight: 400; }.activity-placeholder { padding: 24rpx; border: 1rpx dashed #d4bc98; border-radius: 12rpx; background: #fffaf0; color: var(--muted); font-size: 25rpx; line-height: 1.6; }
</style>
