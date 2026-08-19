import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ensureLogin } from '@/auth/login'
import {
  getCurrentUser,
  getSchools,
  selectUserSchool,
  type SchoolSummary,
  type UserProfile,
} from '@/api/users'

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfile | null>(null)
  const schools = ref<SchoolSummary[]>([])
  const initialized = ref(false)
  let initializePromise: Promise<void> | null = null

  const currentSchool = computed(() => profile.value?.school ?? null)

  async function loadProfile(): Promise<UserProfile> {
    const nextProfile = await getCurrentUser()
    profile.value = nextProfile
    return nextProfile
  }

  const refreshProfile = loadProfile

  async function loadSchools(): Promise<SchoolSummary[]> {
    const nextSchools = await getSchools()
    schools.value = nextSchools
    return nextSchools
  }

  async function initialize(): Promise<void> {
    if (initialized.value) {
      return
    }

    if (!initializePromise) {
      initializePromise = (async () => {
        await ensureLogin()
        await Promise.all([loadProfile(), loadSchools()])
        initialized.value = true
      })().finally(() => {
        initializePromise = null
      })
    }

    await initializePromise
  }

  async function selectSchool(schoolId: string): Promise<UserProfile> {
    const nextProfile = await selectUserSchool(schoolId)
    profile.value = nextProfile
    return nextProfile
  }

  return {
    profile,
    schools,
    initialized,
    currentSchool,
    loadProfile,
    refreshProfile,
    loadSchools,
    initialize,
    selectSchool,
  }
})
