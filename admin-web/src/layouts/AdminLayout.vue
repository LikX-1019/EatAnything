<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, School, Shop, UploadFilled, User, ChatDotSquare, Picture, Key, Document } from '@element-plus/icons-vue'
import PageHeading from '../components/PageHeading.vue'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const collapsed = ref(false)
const items = [
  ['/dashboard', '数据总览', DataAnalysis], ['/schools', '学校管理', School], ['/stores', '店铺管理', Shop],
  ['/imports', '批量导入', UploadFilled], ['/users', '用户管理', User], ['/reviews', '评论管理', ChatDotSquare],
  ['/check-ins', '打卡照片', Picture], ['/admins', '管理员管理', Key], ['/audit-logs', '审计日志', Document],
] as const
const visibleItems = computed(() => items.filter(item => item[0] !== '/admins' || auth.admin?.isPlatformAdmin))
function logout() { auth.logout(); router.replace('/login') }
onMounted(async () => {
  document.documentElement.dataset.font = workspace.fontMode
  if (!auth.admin) await auth.load()
  await workspace.loadSchools()
  // 学校管理员的学校范围由后端返回，界面固定到其第一个绑定学校，不能切换到其他学校。
  if (!auth.admin?.isPlatformAdmin) workspace.schoolId = auth.admin?.schools[0]?.id || ''
})
</script>

<template>
  <div class="admin-shell" :class="{ collapsed }">
    <aside class="journal-sidebar">
      <button class="brand-note" @click="collapsed = !collapsed"><span class="brand-mark">🍱</span><span v-if="!collapsed">校园吃什么<small>管理手账</small></span></button>
      <nav><router-link v-for="item in visibleItems" :key="item[0]" :to="item[0]" :title="item[1]"><el-icon><component :is="item[2]" /></el-icon><span v-if="!collapsed">{{ item[1] }}</span></router-link></nav>
      <div v-if="!collapsed" class="sidebar-sticker">今日也要认真整理 ✦</div>
    </aside>
    <section class="admin-main">
      <header class="topbar">
        <div class="breadcrumb">管理手账 / {{ route.meta.title }}</div>
        <div class="topbar-tools">
          <el-select v-model="workspace.schoolId" placeholder="全部学校" clearable :disabled="!auth.admin?.isPlatformAdmin" class="school-select">
            <el-option v-for="school in workspace.schools" :key="school.id" :label="school.name" :value="school.id" />
          </el-select>
          <button class="font-switch" @click="workspace.setFontMode(workspace.fontMode === 'journal' ? 'system' : 'journal')">字</button>
          <span class="admin-avatar">{{ auth.admin?.displayName?.slice(0, 1) || '管' }}</span>
          <div class="admin-copy"><strong>{{ auth.admin?.displayName || '管理员' }}</strong><small>{{ auth.admin?.isPlatformAdmin ? '平台管理员' : '学校管理员' }}</small></div>
          <el-button text @click="logout">退出</el-button>
        </div>
      </header>
      <main class="page-content">
        <PageHeading :title="String(route.meta.title || '')" :note="String(route.meta.note || '')" />
        <router-view />
      </main>
    </section>
  </div>
</template>
