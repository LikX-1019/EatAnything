<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import { getMessage, markMessageRead, type MessageItem } from '../../api/messages'
import { useMessageStore } from '../../stores/useMessageStore'
import { ApiClientError } from '../../api/types'

const messageStore=useMessageStore();const item=ref<MessageItem|null>(null);const loading=ref(true);const error=ref('')
async function load(id:string){loading.value=true;try{const result=await getMessage(id);item.value=result;if(!result.isRead){await markMessageRead(id);messageStore.consumeRead();result.isRead=true}}catch(e){error.value=e instanceof ApiClientError?e.message:'消息加载失败'}finally{loading.value=false}}
function action(){if(!item.value?.actionType)return;if(item.value.actionType==='stores'){uni.switchTab({url:'/pages/stores/index'});return}const paths:Record<string,string>={reviews:'/pages/reviews/index',checkins:'/pages/checkins/history',settings:'/pages/settings/index',favorites:'/pages/favorites/index',history:'/pages/history/index'};const path=item.value.actionType==='store_detail'&&item.value.actionTargetId?`/pages/stores/detail?storeId=${item.value.actionTargetId}`:paths[item.value.actionType];if(path)uni.navigateTo({url:path})}
onLoad(query=>{if(query?.id)void load(String(query.id));else{loading.value=false;error.value='消息参数缺失'}})
</script>
<template><view class="page-shell detail-page"><PageHeader title="消息详情" back/><view class="page-pad"><view v-if="loading" class="state">正在打开消息…</view><view v-else-if="error" class="state">{{error}}</view><article v-else-if="item" class="message-paper"><view class="tape"/><text class="kind">{{item.kind==='announcement'?'平台公告':'平台通知'}}</text><text class="title">{{item.title}}</text><text class="time">{{new Date(item.publishAt).toLocaleString()}}</text><rich-text class="rich-body" :nodes="item.bodyHtml"/><button v-if="item.actionType" class="action-button" @tap="action">前往查看</button></article></view></view></template>
<style scoped>.page-pad{padding:28rpx}.state{padding:180rpx 20rpx;color:var(--muted);text-align:center}.message-paper{position:relative;padding:34rpx 30rpx;border:1rpx solid var(--line);border-radius:8rpx 14rpx 9rpx 12rpx;background:#fffaf0;box-shadow:var(--paper-shadow)}.tape{position:absolute;top:-13rpx;left:42%;width:110rpx;height:28rpx;background:rgba(232,183,139,.5);transform:rotate(2deg)}.kind{display:block;color:var(--brand);font-size:24rpx;font-weight:900}.title{display:block;margin-top:16rpx;font-size:40rpx;font-weight:900}.time{display:block;margin-top:10rpx;padding-bottom:23rpx;border-bottom:1rpx dashed var(--line);color:var(--muted);font-size:22rpx}.rich-body{display:block;margin-top:26rpx;font-size:29rpx;line-height:1.8}.action-button{width:100%;height:78rpx;margin-top:32rpx;border-radius:10rpx;background:var(--brand);color:#fff;font-size:27rpx;font-weight:900}</style>
