<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const saved = localStorage.getItem('eat_anything_admin_username') || ''
const form = reactive({ username: saved, password: '', remember: Boolean(saved) })
const loading = ref(false)
async function submit() {
  if (!form.username || form.password.length < 8) return ElMessage.warning('请填写管理员账号和至少 8 位密码')
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    if (form.remember) localStorage.setItem('eat_anything_admin_username', form.username)
    else localStorage.removeItem('eat_anything_admin_username')
    await router.replace('/dashboard')
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : '登录失败') }
  finally { loading.value = false }
}
</script>

<template>
  <main class="login-page">
    <span class="login-doodle d1">✿</span><span class="login-doodle d2">✦</span><span class="login-doodle d3">🍙</span>
    <section class="login-paper">
      <span class="login-tape" />
      <div class="login-icon">🍱</div>
      <h1>管理员手账</h1><p>校园吃什么 · Web 管理后台</p>
      <el-form @submit.prevent="submit">
        <el-form-item><el-input v-model="form.username" size="large" placeholder="管理员账号" autocomplete="username" /></el-form-item>
        <el-form-item><el-input v-model="form.password" size="large" type="password" show-password placeholder="密码" autocomplete="current-password" @keyup.enter="submit" /></el-form-item>
        <div class="login-options"><el-checkbox v-model="form.remember">记住账号</el-checkbox><span>仅限管理员访问</span></div>
        <el-button type="primary" size="large" :loading="loading" class="login-button" @click="submit">翻开管理手账</el-button>
      </el-form>
      <div class="login-footer">认真整理，也温柔守护每一条校园记录 ♡</div>
    </section>
  </main>
</template>

<style scoped>
.login-page{position:relative;display:grid;min-height:100vh;overflow:hidden;place-items:center;background-color:var(--page);background-image:linear-gradient(rgba(190,151,101,.16) 1px,transparent 1px),linear-gradient(90deg,rgba(190,151,101,.14) 1px,transparent 1px);background-size:20px 20px}.login-paper{position:relative;width:430px;padding:48px 52px 38px;border:1px solid #d8bd99;background:#fffaf0;box-shadow:0 24px 60px rgba(95,64,35,.2);text-align:center;transform:rotate(-.45deg)}.login-paper::after{position:absolute;right:-18px;bottom:28px;width:70px;height:26px;background:rgba(239,164,139,.4);content:"";transform:rotate(-26deg)}.login-tape{position:absolute;top:-15px;left:174px;width:82px;height:34px;background:rgba(231,201,157,.65);transform:rotate(3deg)}.login-icon{font-size:50px}.login-paper h1{margin-top:12px;font-family:var(--hand-font);font-size:32px;letter-spacing:4px}.login-paper>p{margin:5px 0 32px;color:var(--muted);font-size:13px}.login-options{display:flex;align-items:center;justify-content:space-between;margin:-2px 0 18px;color:var(--muted);font-size:12px}.login-button{width:100%;font-family:var(--hand-font);font-size:17px;font-weight:900}.login-footer{margin-top:27px;color:#9b806a;font-family:var(--hand-font);font-size:13px}.login-doodle{position:absolute;color:var(--brand);font-size:52px;opacity:.35}.d1{top:16%;left:16%;transform:rotate(-18deg)}.d2{right:19%;bottom:19%;color:var(--amber);font-size:70px}.d3{top:25%;right:13%;font-size:62px;transform:rotate(12deg)}
</style>
