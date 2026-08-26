<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type PageData } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

interface Result { totalRows:number;createdCount:number;updatedCount:number;items:Array<Record<string,unknown>> }
const auth=useAuthStore();const workspace=useWorkspaceStore();const file=ref<File|null>(null);const loading=ref(false);const result=ref<Result|null>(null);const error=ref('');const history=ref<Array<Record<string,any>>>([])
async function loadHistory(){const data=await api.get<PageData<Record<string,any>>>('/admin/audit-logs',{action:'store.import',pageSize:10});history.value=data.items}
function choose(upload:{raw?:File}){file.value=upload.raw||null;result.value=null;error.value=''}
async function submit(){if(!workspace.schoolId)return ElMessage.warning('请先选择要导入的学校');if(!file.value)return ElMessage.warning('请先选择 CSV 或 XLSX 文件');const data=new FormData();data.append('file',file.value);data.append('schoolId',workspace.schoolId);loading.value=true;error.value='';try{result.value=await api.post<Result>('/admin/stores/import',data);ElMessage.success('批量导入完成');await loadHistory()}catch(e){error.value=e instanceof Error?e.message:'导入失败'}finally{loading.value=false}}
function template(){const csv='食堂,店铺位置,店铺名称,店铺图片\n';const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='店铺导入模板.csv';a.click();URL.revokeObjectURL(url)}
onMounted(loadHistory)
</script>
<template>
  <section class="paper-card upload-scrap"><div><div class="upload-icon">📎</div><h3>把店铺表格贴进管理手账</h3><p>先选择目标学校，再上传 UTF-8 CSV 或 XLSX。最多 1000 行；任何一行有误都会整批回滚。</p><el-select v-model="workspace.schoolId" :disabled="!auth.admin?.isPlatformAdmin" placeholder="请选择导入学校" style="width:280px;margin-bottom:14px"><el-option v-for="school in workspace.schools" :key="school.id" :label="school.name" :value="school.id"/></el-select><el-upload :auto-upload="false" :limit="1" accept=".csv,.xlsx" :on-change="choose"><el-button type="primary">选择文件</el-button></el-upload><p v-if="file"><strong>{{ file.name }}</strong> · {{ (file.size/1024).toFixed(1) }} KB</p><div><el-button text @click="template">下载中文 CSV 模板</el-button><el-button type="success" :loading="loading" :disabled="!file||!workspace.schoolId" @click="submit">校验并导入</el-button></div><div v-if="error" class="error-note">✎ {{ error }}</div></div></section>
  <section v-if="result" class="stats-grid" style="margin-top:20px"><article class="paper-card stat-card"><div class="stat-label">数据行</div><div class="stat-value">{{ result.totalRows }}</div></article><article class="paper-card stat-card"><div class="stat-label">新增店铺</div><div class="stat-value">{{ result.createdCount }}</div></article><article class="paper-card stat-card"><div class="stat-label">更新店铺</div><div class="stat-value">{{ result.updatedCount }}</div></article></section>
  <section class="paper-card table-paper" style="margin-top:20px"><div class="table-toolbar"><h3>导入规则便签</h3></div><div class="activity-list"><div class="activity-item">模板只有四列：食堂、店铺位置、店铺名称、店铺图片。</div><div class="activity-item">食堂必须填写目标学校中已启用的食堂名称（也支持填写区域编码）。</div><div class="activity-item">店铺图片只能填写 HTTP(S) URL，不能把图片文件放进表格；图片必须是系统已上传的媒体地址。</div><div class="activity-item">导入后店铺会自动归档到所选学校和食堂，默认上架并自动生成店铺编码。</div><div class="activity-item">学校管理员只能导入自己被授权学校的店铺。</div></div></section>
  <section class="paper-card table-paper" style="margin-top:20px"><div class="table-toolbar"><h3>最近导入记录</h3></div><el-table :data="history"><el-table-column label="时间" width="180"><template #default="s">{{ new Date(s.row.createdAt).toLocaleString() }}</template></el-table-column><el-table-column prop="operator" label="管理员" width="140"/><el-table-column prop="targetId" label="文件" min-width="220"/><el-table-column prop="reason" label="结果摘要" min-width="220"/></el-table></section>
</template>
