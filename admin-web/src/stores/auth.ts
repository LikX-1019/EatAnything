import { defineStore } from 'pinia'
import { api, clearToken, getToken, setToken } from '../api/client'

export interface AdminSession {
  id: string
  username: string
  displayName: string
  role: string
  isPlatformAdmin: boolean
  schools: Array<{ id: string; name: string; schoolCode: string }>
}

export const useAuthStore = defineStore('auth', {
  state: () => ({ admin: null as AdminSession | null, loading: false }),
  getters: { authenticated: () => Boolean(getToken()) },
  actions: {
    async login(username: string, password: string) {
      const data = await api.post<{ accessToken: string }>('/admin/auth/login', { username, password })
      setToken(data.accessToken)
      await this.load()
    },
    async load() {
      if (!getToken()) return
      this.loading = true
      try { this.admin = await api.get<AdminSession>('/admin/me') }
      finally { this.loading = false }
    },
    logout() { clearToken(); this.admin = null },
  },
})
