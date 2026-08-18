<script setup lang="ts">
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'

const appStore = useAppStore()

function chooseFont(preference: 'cheese' | 'system') {
  appStore.setFontPreference(preference)
  uni.showToast({ title: preference === 'cheese' ? '已使用奶酪体' : '已跟随系统字体', icon: 'none' })
}
</script>

<template>
  <view class="page-shell settings-page" :class="appStore.fontClass">
    <PageHeader title="设置" back />
    <view class="page-pad">
      <view class="section-label"><text>✎ 字体风格</text><text>选择后立即生效</text></view>
      <view class="font-sheet">
        <view class="sheet-tape" />
        <view class="font-option" :class="{ active: appStore.fontPreference === 'cheese' }" @tap="chooseFont('cheese')">
          <view class="option-copy">
            <text class="option-name">奶酪体</text>
            <text class="option-description">默认字体 · 圆润可爱的手账风</text>
            <text class="font-preview cheese-preview">今天吃什么？一起去发现好味道</text>
          </view>
          <view class="radio"><text v-if="appStore.fontPreference === 'cheese'">✓</text></view>
        </view>
        <view class="font-option" :class="{ active: appStore.fontPreference === 'system' }" @tap="chooseFont('system')">
          <view class="option-copy">
            <text class="option-name system-preview">系统字体</text>
            <text class="option-description system-preview">使用手机或电脑当前的默认字体</text>
            <text class="font-preview system-preview">今天吃什么？一起去发现好味道</text>
          </view>
          <view class="radio"><text v-if="appStore.fontPreference === 'system'">✓</text></view>
        </view>
      </view>
      <view class="tip-note"><text class="tip-icon">💡</text><text>字体选择会自动保存在当前设备，下次打开仍会继续使用。</text></view>
    </view>
  </view>
</template>

<style scoped>
.settings-page { background: transparent; }
.page-pad { padding: 18rpx 30rpx; }
.section-label { display: flex; align-items: center; justify-content: space-between; margin: 8rpx 6rpx 18rpx; }
.section-label text:first-child { font-size: 34rpx; font-weight: 900; }
.section-label text:last-child { color: var(--muted); font-size: 24rpx; }
.font-sheet { position: relative; padding: 24rpx; border: 1rpx solid #dfc7a5; background-color: #fffaf0; background-image: linear-gradient(rgba(213,181,139,.12) 1rpx, transparent 1rpx); background-size: 100% 44rpx; box-shadow: var(--paper-shadow); transform: rotate(-.2deg); }
.sheet-tape { position: absolute; top: -13rpx; left: calc(50% - 55rpx); width: 110rpx; height: 30rpx; background: rgba(236,180,147,.5); transform: rotate(2deg); }
.font-option { display: flex; align-items: center; min-height: 190rpx; padding: 24rpx 22rpx; border: 2rpx dashed #dfccb0; border-radius: 14rpx 8rpx 15rpx 10rpx; background: rgba(255,255,255,.52); }
.font-option + .font-option { margin-top: 18rpx; }
.font-option.active { border-style: solid; border-color: #df8b76; background: #fff1e8; box-shadow: 0 5rpx 12rpx rgba(118,76,45,.09); }
.option-copy { min-width: 0; flex: 1; }
.option-name, .option-description, .font-preview { display: block; }
.option-name { font-size: 36rpx; font-weight: 900; }
.option-description { margin-top: 7rpx; color: var(--muted); font-size: 25rpx; }
.font-preview { margin-top: 22rpx; color: #6d4e37; font-size: 31rpx; }
.cheese-preview { font-family: "ZQKNLT", "Cheese Local", "小可奶酪体", "Kaiti SC", "STKaiti", "KaiTi", cursive; }
.system-preview { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif; }
.radio { display: flex; align-items: center; justify-content: center; width: 46rpx; height: 46rpx; margin-left: 18rpx; border: 2rpx solid #cdb79a; border-radius: 50%; color: #fff; font-size: 25rpx; font-weight: 900; }
.active .radio { border-color: var(--brand); background: var(--brand); }
.tip-note { display: flex; gap: 13rpx; margin-top: 26rpx; padding: 18rpx 20rpx; border: 1rpx dashed #d2b990; border-radius: 10rpx; background: rgba(255,247,226,.75); color: var(--muted); font-size: 25rpx; line-height: 1.55; }
.tip-icon { flex: 0 0 auto; }
</style>
