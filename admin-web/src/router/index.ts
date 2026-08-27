import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api/client'

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  {
    path: '/', component: () => import('../layouts/AdminLayout.vue'), redirect: '/dashboard', children: [
      { path: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '数据总览', note: '今天的校园小记' } },
      { path: 'schools', component: () => import('../views/SchoolsView.vue'), meta: { title: '学校管理', note: '一校一册，清楚归档' } },
      { path: 'stores', component: () => import('../views/StoresView.vue'), meta: { title: '店铺管理', note: '把好吃的小店贴进手账' } },
      { path: 'imports', component: () => import('../views/ImportsView.vue'), meta: { title: '批量导入', note: '一次整理好多家店铺' } },
      { path: 'users', component: () => import('../views/UsersView.vue'), meta: { title: '用户管理', note: '每位同学都有自己的档案卡' } },
      { path: 'reviews', component: () => import('../views/ReviewsView.vue'), meta: { title: '评论管理', note: '认真收好每一条评价' } },
      { path: 'check-ins', component: () => import('../views/CheckInsView.vue'), meta: { title: '打卡照片', note: '校园里的每一餐留影' } },
      { path: 'admins', component: () => import('../views/AdminsView.vue'), meta: { title: '管理员管理', note: '一起维护这本校园手账', platformOnly: true } },
      { path: 'audit-logs', component: () => import('../views/AuditLogsView.vue'), meta: { title: '审计日志', note: '重要操作都有迹可循' } },
    ],
  },
]

const router = createRouter({ history: createWebHistory('/admin/'), routes })
router.beforeEach((to) => {
  if (!to.meta.public && !getToken()) return '/login'
  if (to.path === '/login' && getToken()) return '/dashboard'
})
export default router
