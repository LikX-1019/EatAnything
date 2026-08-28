<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type PageData } from '../api/client'
import RichTextEditor from '../components/RichTextEditor.vue'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

interface MessageItem{id:string;kind:'notification'|'announcement';title:string;bodyHtml:string;targetType:'all'|'school'|'user';schoolId?:string;userId?:string;priority:string;status:string;displayStatus:string;wechatPush:boolean;publishAt?:string;expireAt?:string;createdAt:string;mediaIds?:string[];estimate?:{inApp:number;wechat:number};delivery?:Record<string,number>}
const auth=useAuthStore();const workspace=useWorkspaceStore();const rows=ref<MessageItem[]>([]);const total=ref(0);const loading=ref(false);const dialog=ref(false);const editingId=ref('');const readOnly=ref(false);const delivery=ref<Record<string,number>>({})
const filters=reactive({kind:'',status:'',page:1,pageSize:20})
const form=reactive({kind:'notification' as 'notification'|'announcement',title:'',bodyHtml:'<p></p>',targetType:'school' as 'all'|'school'|'user',schoolId:'',userId:'',priority:'normal',actionType:'',actionTargetId:'',wechatPush:false,publishAt:'',expireAt:'',mediaIds:[] as string[]})
const estimate=reactive({inApp:0,wechat:0})
const actionOptions=[['','不跳转'],['reviews','我的评价'],['checkins','打卡记录'],['settings','设置'],['favorites','我的收藏'],['history','历史记录'],['stores','店铺列表'],['store_detail','指定店铺详情']]
const statusLabels:Record<string,string>={draft:'草稿',scheduled:'待发布',active:'展示中',expired:'已失效',revoked:'已撤回'}
const targetLabel=(item:MessageItem)=>item.targetType==='all'?'全平台':item.targetType==='school'?`学校 ${item.schoolId}`:`用户 ${item.userId}`
const canAll=computed(()=>Boolean(auth.admin?.isPlatformAdmin))
function toLocal(value?:string){if(!value)return '';const date=new Date(value);const offset=date.getTimezoneOffset()*60000;return new Date(date.getTime()-offset).toISOString().slice(0,16)}
function toIso(value:string){return value?new Date(value).toISOString():null}
async function load(){loading.value=true;try{const data=await api.get<PageData<MessageItem>>('/admin/messages',{...filters,schoolId:workspace.schoolId});rows.value=data.items;total.value=data.total}finally{loading.value=false}}
function reset(){editingId.value='';Object.assign(estimate,{inApp:0,wechat:0});Object.assign(form,{kind:'notification',title:'',bodyHtml:'<p></p>',targetType:canAll.value?'all':'school',schoolId:canAll.value?'':String(auth.admin?.schools[0]?.id||workspace.schoolId||''),userId:'',priority:'normal',actionType:'',actionTargetId:'',wechatPush:false,publishAt:'',expireAt:'',mediaIds:[]})}
function create(){reset();readOnly.value=false;delivery.value={};dialog.value=true}
async function edit(item:MessageItem,viewOnly=false){const detail=await api.get<MessageItem>(`/admin/messages/${item.id}`);editingId.value=item.id;readOnly.value=viewOnly;delivery.value=detail.delivery||{};Object.assign(estimate,detail.estimate||{inApp:0,wechat:0});Object.assign(form,{kind:detail.kind,title:detail.title,bodyHtml:detail.bodyHtml,targetType:detail.targetType,schoolId:detail.schoolId||'',userId:detail.userId||'',priority:detail.priority,actionType:(detail as any).actionType||'',actionTargetId:(detail as any).actionTargetId||'',wechatPush:detail.wechatPush,publishAt:toLocal(detail.publishAt),expireAt:toLocal(detail.expireAt),mediaIds:detail.mediaIds||[]});dialog.value=true}
function payload(){return {kind:form.kind,title:form.title,bodyHtml:form.bodyHtml,targetType:form.targetType,schoolId:form.targetType==='school'?Number(form.schoolId):null,userId:form.targetType==='user'?Number(form.userId):null,priority:form.priority,actionType:form.actionType||null,actionTargetId:form.actionType==='store_detail'?Number(form.actionTargetId):null,wechatPush:form.wechatPush,publishAt:toIso(form.publishAt),expireAt:toIso(form.expireAt),mediaIds:form.mediaIds.map(Number)}}
async function save(){try{if(editingId.value)await api.patch(`/admin/messages/${editingId.value}`,payload());else{const result=await api.post<MessageItem>('/admin/messages',payload());editingId.value=result.id;Object.assign(estimate,result.estimate||{inApp:0,wechat:0})}ElMessage.success('消息草稿已保存');dialog.value=false;await load()}catch(error){ElMessage.error(error instanceof Error?error.message:'保存失败')}}
async function publish(item?:MessageItem){const id=item?.id||editingId.value;if(!id){await save();return}try{const preview=await api.get<MessageItem>(`/admin/messages/${id}`);Object.assign(estimate,preview.estimate||{inApp:0,wechat:0});await ElMessageBox.confirm(`预计站内接收 ${estimate.inApp} 人，微信可发送 ${estimate.wechat} 人。发布后生效前可编辑，生效后只能撤回。确定发布吗？`,'发布确认',{type:'warning'});const result=await api.post<any>(`/admin/messages/${id}/publish`);ElMessage.success(`发布成功：站内预计 ${result.estimate?.inApp||0} 人，微信预计 ${result.estimate?.wechat||0} 人`);dialog.value=false;await load()}catch(error){if(error!=='cancel'&&error!=='close')ElMessage.error(error instanceof Error?error.message:'发布失败')}}
async function revoke(item:MessageItem){try{await ElMessageBox.confirm('撤回后用户将无法再看到该消息。','撤回消息',{type:'warning'});await api.post(`/admin/messages/${item.id}/revoke`);ElMessage.success('消息已撤回');await load()}catch(error){if(error!=='cancel'&&error!=='close')ElMessage.error(error instanceof Error?error.message:'撤回失败')}}
onMounted(load);watch(()=>workspace.schoolId,()=>{filters.page=1;load()})
</script>

<template>
  <section class="paper-card filter-paper">
    <el-select v-model="filters.kind" placeholder="全部类型" clearable style="width:150px"><el-option label="通知" value="notification"/><el-option label="公告" value="announcement"/></el-select>
    <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:150px"><el-option label="草稿" value="draft"/><el-option label="已发布" value="published"/><el-option label="已撤回" value="revoked"/></el-select>
    <el-button type="primary" @click="load">筛选</el-button><el-button style="margin-left:auto" type="primary" @click="create">新建通知或公告</el-button>
      </section>
  <section class="paper-card table-paper"><div class="table-toolbar"><h3>通知公告 · {{total}} 条</h3></div>
    <el-table v-loading="loading" :data="rows" row-key="id"><el-table-column label="类型" width="85"><template #default="s">{{s.row.kind==='announcement'?'公告':'通知'}}</template></el-table-column><el-table-column prop="title" label="标题" min-width="220"/><el-table-column label="范围" width="150"><template #default="s">{{targetLabel(s.row)}}</template></el-table-column><el-table-column label="状态" width="100"><template #default="s"><span class="status-sticker" :class="`is-${s.row.displayStatus}`">{{statusLabels[s.row.displayStatus]}}</span></template></el-table-column><el-table-column label="发布时间" width="175"><template #default="s">{{s.row.publishAt?new Date(s.row.publishAt).toLocaleString():'—'}}</template></el-table-column><el-table-column label="微信" width="75"><template #default="s">{{s.row.wechatPush?'同步':'站内'}}</template></el-table-column><el-table-column label="操作" width="250" fixed="right"><template #default="s"><el-button link @click="edit(s.row,true)">详情</el-button><el-button link @click="edit(s.row)" :disabled="s.row.displayStatus==='active'||s.row.displayStatus==='expired'||s.row.displayStatus==='revoked'">编辑</el-button><el-button v-if="s.row.status==='draft'" link type="primary" @click="publish(s.row)">发布</el-button><el-button v-if="s.row.status==='published'&&s.row.displayStatus!=='expired'" link type="danger" @click="revoke(s.row)">撤回</el-button></template></el-table-column></el-table>
    <div class="pagination-row"><el-pagination v-model:current-page="filters.page" layout="total, prev, pager, next" :total="total" @current-change="load"/></div>
  </section>
  <el-drawer v-model="dialog" :title="editingId?'编辑消息草稿':'新建通知或公告'" size="820px">
    <el-form label-position="top" :disabled="readOnly"><div class="form-grid">
      <el-form-item label="类型"><el-radio-group v-model="form.kind" :disabled="Boolean(editingId)"><el-radio-button value="notification">通知</el-radio-button><el-radio-button value="announcement">公告</el-radio-button></el-radio-group></el-form-item>
      <el-form-item label="优先级"><el-select v-model="form.priority" style="width:100%"><el-option label="普通" value="normal"/><el-option label="重要" value="important"/></el-select></el-form-item>
      <el-form-item label="标题" class="wide"><el-input v-model="form.title" maxlength="120" show-word-limit/></el-form-item>
      <el-form-item label="接收范围"><el-select v-model="form.targetType" style="width:100%"><el-option v-if="canAll" label="全平台" value="all"/><el-option label="指定学校" value="school"/><el-option label="指定用户" value="user"/></el-select></el-form-item>
      <el-form-item v-if="form.targetType==='school'" label="学校"><el-select v-model="form.schoolId" filterable style="width:100%"><el-option v-for="school in workspace.schools" :key="school.id" :label="school.name" :value="school.id"/></el-select></el-form-item>
      <el-form-item v-if="form.targetType==='user'" label="用户 ID"><el-input v-model="form.userId" placeholder="请输入管理后台用户列表中的 ID"/></el-form-item>
      <el-form-item label="微信推送"><el-switch v-model="form.wechatPush"/><small class="form-help">仅已授权对应模板的用户会收到；用户自身操作仍只发站内通知。</small></el-form-item>
      <el-form-item label="发布时间"><el-date-picker v-model="form.publishAt" type="datetime" value-format="YYYY-MM-DDTHH:mm" placeholder="留空表示发布时立即生效" style="width:100%"/></el-form-item>
      <el-form-item label="失效时间"><el-date-picker v-model="form.expireAt" type="datetime" value-format="YYYY-MM-DDTHH:mm" clearable style="width:100%"/></el-form-item>
      <el-form-item label="站内跳转"><el-select v-model="form.actionType" style="width:100%"><el-option v-for="item in actionOptions" :key="item[0]" :label="item[1]" :value="item[0]"/></el-select></el-form-item>
      <el-form-item v-if="form.actionType==='store_detail'" label="店铺 ID"><el-input v-model="form.actionTargetId"/></el-form-item>
      <el-form-item label="正文" class="wide"><RichTextEditor v-model="form.bodyHtml" v-model:media-ids="form.mediaIds"/></el-form-item>
      <div v-if="editingId" class="wide filter-note">发布预估：站内 {{estimate.inApp}} 人 · 微信已授权 {{estimate.wechat}} 人</div>
      <div v-if="editingId" class="wide filter-note">微信任务：待发送 {{(delivery.pending||0)+(delivery.retry||0)}} · 已发送 {{delivery.sent||0}} · 失败 {{delivery.failed||0}} · 跳过 {{delivery.skipped||0}}</div>
    </div></el-form>
    <template #footer><el-button @click="dialog=false">{{readOnly?'关闭':'取消'}}</el-button><template v-if="!readOnly"><el-button type="primary" @click="save">保存草稿</el-button><el-button v-if="editingId" type="success" @click="publish()">发布</el-button></template></template>
  </el-drawer>
</template>
