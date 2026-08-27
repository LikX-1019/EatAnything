<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { api, type PageData } from '../api/client'
import { useWorkspaceStore } from '../stores/workspace'

interface LogItem{id:string;operator:string;schoolName?:string;action:string;targetType:string;targetId:string;reason?:string;ipAddress?:string;createdAt:string}
const workspace=useWorkspaceStore();const rows=ref<LogItem[]>([]);const total=ref(0);const loading=ref(false);const filters=reactive({action:'',page:1,pageSize:20})
const labels:Record<string,string>={'school.create':'新增学校','school.update':'修改学校','area.create':'新增区域','area.update':'修改区域','user.update':'修改用户','review.hide':'隐藏评论','review.restore':'恢复评论','check_in.hide':'隐藏打卡','check_in.restore':'恢复打卡','admin.create':'新增管理员','admin.update':'修改管理员'}
async function load(){loading.value=true;try{const data=await api.get<PageData<LogItem>>('/admin/audit-logs',{...filters,schoolId:workspace.schoolId});rows.value=data.items;total.value=data.total}finally{loading.value=false}}
function exportCsv(){const header=['时间','管理员','学校','操作','目标','原因','IP'];const lines=rows.value.map(i=>[new Date(i.createdAt).toLocaleString(),i.operator,i.schoolName||'',labels[i.action]||i.action,`${i.targetType}:${i.targetId}`,i.reason||'',i.ipAddress||''].map(v=>`"${String(v).replaceAll('"','""')}"`).join(','));const url=URL.createObjectURL(new Blob(['\ufeff'+[header.join(','),...lines].join('\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='管理员审计日志.csv';a.click();URL.revokeObjectURL(url)}
onMounted(load);watch(()=>workspace.schoolId,()=>{filters.page=1;load()})
</script>
<template>
  <section class="paper-card filter-paper"><el-input v-model="filters.action" placeholder="操作编码，如 review.hide" clearable style="width:260px"/><el-button type="primary" @click="load">筛选记录</el-button><el-button style="margin-left:auto" @click="exportCsv">导出当前页 CSV</el-button></section>
  <section class="paper-card table-paper"><div class="table-toolbar"><h3>不可修改的操作足迹 · {{ total }} 条</h3></div><el-table v-loading="loading" :data="rows" row-key="id"><el-table-column label="时间" width="180"><template #default="s">{{ new Date(s.row.createdAt).toLocaleString() }}</template></el-table-column><el-table-column prop="operator" label="管理员" width="140"/><el-table-column prop="schoolName" label="学校" min-width="150"/><el-table-column label="操作" width="150"><template #default="s"><span class="status-sticker is-active">{{ labels[s.row.action]||s.row.action }}</span></template></el-table-column><el-table-column label="目标" width="170"><template #default="s"><span class="mono">{{ s.row.targetType }}:{{ s.row.targetId }}</span></template></el-table-column><el-table-column label="处理原因" min-width="220"><template #default="s">{{ s.row.reason||'—' }}</template></el-table-column><el-table-column prop="ipAddress" label="IP" width="140"/></el-table><div class="pagination-row"><el-pagination v-model:current-page="filters.page" layout="total, prev, pager, next" :total="total" @current-change="load"/></div></section>
</template>
