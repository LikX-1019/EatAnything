import { defineStore } from 'pinia'
import { api } from '../api/client'

export interface SchoolOption { id: string; schoolCode: string; name: string; status: string; areas: Array<Record<string, any>> }

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({ schools: [] as SchoolOption[], schoolId: '', fontMode: localStorage.getItem('admin_font_mode') || 'journal' }),
  actions: {
    async loadSchools() { this.schools = await api.get<SchoolOption[]>('/admin/schools') },
    setFontMode(value: string) { this.fontMode = value; localStorage.setItem('admin_font_mode', value); document.documentElement.dataset.font = value },
  },
})
