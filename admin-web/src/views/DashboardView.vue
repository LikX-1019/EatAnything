<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '../api/client'
import { useWorkspaceStore } from '../stores/workspace'

interface Summary { schoolCount: number; storeCount: number; userCount: number; reviewCount: number; checkInCount: number; hiddenContentCount: number }
const workspace = useWorkspaceStore()
const summary = ref<Summary>({ schoolCount: 0, storeCount: 0, userCount: 0, reviewCount: 0, checkInCount: 0, hiddenContentCount: 0 })
const cards = [
  ['学校数量','schoolCount','✿'],['店铺数量','storeCount','🍜'],['用户数量','userCount','☺'],
  ['评论总数','reviewCount','✎'],['打卡总数','checkInCount','📷'],['隐藏内容','hiddenContentCount','♡'],
] as const
async function load() { summary.value = await api.get<Summary>('/admin/dashboard/summary', { schoolId: workspace.schoolId }) }
onMounted(load); watch(() => workspace.schoolId, load)
</script>
<template>
  <section class="stats-grid"><article v-for="card in cards" :key="card[1]" class="paper-card stat-card"><div class="stat-label">{{ card[0] }}</div><div class="stat-value">{{ summary[card[1]] }}</div><span class="stat-doodle">{{ card[2] }}</span></article></section>
  <section class="dashboard-grid">
    <article class="paper-card chart-card"><div class="table-toolbar"><h3>最近七日校园活跃度</h3><span class="status-sticker is-active">持续更新</span></div><div class="chart-placeholder"><span v-for="height in [35,48,42,68,55,76,64]" :key="height" class="chart-bar" :style="{height:`${height}%`}" /></div></article>
    <article class="paper-card chart-card"><div class="table-toolbar"><h3>管理小贴士</h3><span>✦</span></div><div class="activity-list"><div class="activity-item">隐藏内容前请填写清晰的处理原因。</div><div class="activity-item">学校管理员只能查看已绑定学校的数据。</div><div class="activity-item">店铺批量导入会先校验，错误时整批回滚。</div><div class="activity-item">所有治理操作都会写入审计日志。</div></div></article>
  </section>
</template>
