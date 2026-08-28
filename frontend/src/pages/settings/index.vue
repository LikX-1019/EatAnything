<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import { useAppStore } from '../../stores/useAppStore'
import { useUserStore } from '../../stores/useUserStore'
import { getNotificationSettings, saveWechatConsent, updateNotificationSettings, type NotificationSettings } from '../../api/messages'
import { ApiClientError } from '../../api/types'
import { updateProfile, uploadAvatar, type ProfileUpdate } from '../../api/users'

const appStore = useAppStore()
const userStore = useUserStore()
const notificationSettings=ref<NotificationSettings|null>(null);const subscribing=ref(false)
const GENDER_OPTIONS = [
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
  { value: 'other', label: '其他' },
  { value: 'secret', label: '保密' },
] as const
const nickname=ref('')
const slogan=ref('')
const gender=ref<string>('')
const birthday=ref('')
const genderIndex=ref(0)
const avatarTempPath=ref('')
const savingProfile=ref(false)
function todayIso():string{const d=new Date();const mm=String(d.getMonth()+1).padStart(2,'0');const dd=String(d.getDate()).padStart(2,'0');return `${d.getFullYear()}-${mm}-${dd}`}
const today=todayIso()

function chooseFont(preference: 'cheese' | 'system') {
  appStore.setFontPreference(preference)
  uni.showToast({ title: preference === 'cheese' ? '已使用奶酪体' : '已跟随系统字体', icon: 'none' })
}
async function loadNotificationSettings(){try{notificationSettings.value=await getNotificationSettings()}catch{/* 设置页其他功能仍可使用。 */}}
async function subscribeWechat(){
  // #ifdef MP-WEIXIN
  const settings=notificationSettings.value;if(!settings?.available)return uni.showToast({title:'微信提醒尚未配置',icon:'none'})
  const ids=[settings.templates.notification.templateId,settings.templates.announcement.templateId].filter(Boolean) as string[]
  if(!ids.length)return uni.showToast({title:'微信模板尚未配置',icon:'none'})
  subscribing.value=true
  try{
    const result=await new Promise<Record<string,string>>((resolve,reject)=>uni.requestSubscribeMessage({tmplIds:ids,success:value=>resolve(value as unknown as Record<string,string>),fail:reject}))
    const payload:any={};const notificationId=settings.templates.notification.templateId;const announcementId=settings.templates.announcement.templateId
    if(notificationId&&result[notificationId])payload.notification=result[notificationId]
    if(announcementId&&result[announcementId])payload.announcement=result[announcementId]
    notificationSettings.value=await saveWechatConsent(payload)
    uni.showToast({title:Object.values(payload).includes('accept')?'微信提醒已开启':'未获得微信提醒授权',icon:'none'})
  }catch(error){uni.showToast({title:error instanceof ApiClientError?error.message:'微信授权未完成',icon:'none'})}finally{subscribing.value=false}
  // #endif
}
async function toggleWechat(value:boolean){try{await updateNotificationSettings(value);if(notificationSettings.value)notificationSettings.value.wechatEnabled=value}catch(error){uni.showToast({title:error instanceof ApiClientError?error.message:'设置失败',icon:'none'})}}
function onWechatToggle(event:unknown){void toggleWechat(Boolean((event as {detail?:{value?:boolean}}).detail?.value))}
function loadProfileForm(){
  const profile=userStore.profile
  nickname.value=profile?.nickname??''
  slogan.value=profile?.slogan??''
  gender.value=profile?.gender??''
  birthday.value=profile?.birthday??''
  genderIndex.value=Math.max(0,GENDER_OPTIONS.findIndex(item=>item.value===gender.value))
  avatarTempPath.value=''
}
function onChooseAvatar(event:unknown){
  const detail=(event as {detail?:{avatarUrl?:string}}).detail
  if(detail?.avatarUrl)avatarTempPath.value=detail.avatarUrl
}
function onGenderChange(event:unknown){
  const value=Number((event as {detail?:{value?:number}}).detail?.value??0)
  gender.value=GENDER_OPTIONS[value]?.value??''
}
function onBirthdayChange(event:unknown){
  birthday.value=String((event as {detail?:{value?:string}}).detail?.value??'')
}
async function saveProfile(){
  savingProfile.value=true
  try{
    if(avatarTempPath.value){
      await uploadAvatar(avatarTempPath.value)
      avatarTempPath.value=''
    }
    const payload:ProfileUpdate={}
    if(nickname.value.trim())payload.nickname=nickname.value.trim()
    payload.slogan=slogan.value.trim()||null
    payload.gender=(gender.value as ProfileUpdate['gender'])||null
    payload.birthday=birthday.value||null
    const next=await updateProfile(payload)
    userStore.profile=next
    uni.showToast({title:'资料已保存',icon:'success'})
  }catch(error){
    uni.showToast({title:error instanceof ApiClientError?error.message:'资料保存失败',icon:'none'})
  }finally{
    savingProfile.value=false
  }
}
onShow(()=>{void loadNotificationSettings();void userStore.initialize().then(loadProfileForm)})
</script>

<template>
  <view class="page-shell settings-page" :class="appStore.fontClass">
    <PageHeader title="设置" back />
    <view class="page-pad">
      <view class="section-label profile-label"><text>✎ 个人资料</text><text>微信端可一键填充头像昵称</text></view>
      <view class="profile-sheet">
        <!-- #ifdef MP-WEIXIN -->
        <view class="profile-avatar-row">
          <image v-if="avatarTempPath||userStore.profile?.avatarUrl" class="profile-avatar" :src="avatarTempPath||userStore.profile?.avatarUrl||''" mode="aspectFill" />
          <view v-else class="profile-avatar avatar-placeholder">👩🏻‍🍳</view>
          <button class="avatar-button" open-type="chooseAvatar" @chooseavatar="onChooseAvatar">选择微信头像</button>
        </view>
        <!-- #endif -->
        <view class="profile-row"><text class="profile-label">昵称</text><input v-model="nickname" class="profile-input" maxlength="80" placeholder="请输入昵称" placeholder-class="profile-placeholder" /></view>
        <view class="profile-row"><text class="profile-label">签名</text><input v-model="slogan" class="profile-input" maxlength="255" placeholder="一句话介绍自己" placeholder-class="profile-placeholder" /></view>
        <view class="profile-row"><text class="profile-label">性别</text><picker mode="selector" :range="GENDER_OPTIONS.map(item=>item.label)" :value="genderIndex" @change="onGenderChange"><view class="profile-picker">{{ GENDER_OPTIONS[genderIndex].label }}</view></picker></view>
        <view class="profile-row"><text class="profile-label">生日</text><picker mode="date" :value="birthday" start="1900-01-01" :end="today" @change="onBirthdayChange"><view class="profile-picker">{{ birthday || '选择日期' }}</view></picker></view>
        <button class="save-profile-button" :disabled="savingProfile" @tap="saveProfile">{{ savingProfile ? '保存中…' : '保存资料' }}</button>
      </view>
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
      <!-- #ifdef MP-WEIXIN -->
      <view class="section-label notification-label"><text>✉ 微信消息提醒</text><text>由你主动授权</text></view>
      <view class="notification-sheet">
        <view class="notification-row"><view><text class="option-name">接收微信提醒</text><text class="option-description">重要公告、内容治理和账号状态变化会同步提醒</text></view><switch :checked="notificationSettings?.wechatEnabled!==false" color="#e8755f" @change="onWechatToggle"/></view>
        <view class="template-state"><text>通知模板：{{notificationSettings?.templates.notification.status||'unknown'}}</text><text>公告模板：{{notificationSettings?.templates.announcement.status||'unknown'}}</text></view>
        <button class="subscribe-button" :disabled="subscribing||!notificationSettings?.available" @tap="subscribeWechat">{{subscribing?'正在请求授权…':'授权通知与公告提醒'}}</button>
      </view>
      <!-- #endif -->
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
.notification-label{margin-top:40rpx}.notification-sheet{padding:24rpx;border:1rpx solid #dfc7a5;border-radius:12rpx;background:#fffaf0;box-shadow:var(--paper-shadow)}.notification-row{display:flex;align-items:center;justify-content:space-between;gap:20rpx}.template-state{display:flex;gap:22rpx;margin-top:22rpx;color:var(--muted);font-size:22rpx}.subscribe-button{width:100%;height:76rpx;margin-top:24rpx;border-radius:10rpx;background:var(--brand);color:#fff;font-size:27rpx;font-weight:900}.subscribe-button[disabled]{opacity:.55}
.profile-label{margin-bottom:18rpx}.profile-sheet{padding:24rpx;border:1rpx solid #dfc7a5;border-radius:12rpx;background:#fffaf0;box-shadow:var(--paper-shadow)}.profile-avatar-row{display:flex;align-items:center;gap:26rpx;margin-bottom:20rpx}.profile-avatar{display:flex;align-items:center;justify-content:center;width:118rpx;height:118rpx;border:4rpx solid #fff;border-radius:50%;background:#f7dfc9;font-size:52rpx;box-shadow:0 0 0 2rpx #e7c7ad}.avatar-button{padding:0 24rpx;height:64rpx;border-radius:10rpx;background:var(--brand);color:#fff;font-size:24rpx}.profile-row{display:flex;align-items:center;min-height:82rpx;border-bottom:1rpx dashed #e6d8c2}.profile-label{flex:0 0 96rpx;color:var(--brand-deep);font-size:26rpx;font-weight:800}.profile-input{flex:1;height:78rpx;font-size:27rpx}.profile-placeholder{color:#b7a48f}.profile-picker{display:flex;align-items:center;min-height:78rpx;font-size:27rpx}.save-profile-button{width:100%;height:76rpx;margin-top:22rpx;border-radius:10rpx;background:var(--brand);color:#fff;font-size:27rpx;font-weight:900;box-shadow:0 5rpx 0 #c75f4b}.save-profile-button[disabled]{opacity:.55}
</style>
