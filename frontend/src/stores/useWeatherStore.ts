import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getCurrentSchoolWeather, type SchoolWeatherData } from '@/api/users'
import { useUserStore } from './useUserStore'


export const useWeatherStore = defineStore('weather', () => {
  const userStore = useUserStore()
  const weatherBySchool = ref<Record<string, SchoolWeatherData>>({})
  const attemptedBySchool = ref<Record<string, boolean>>({})
  const loadingSchoolId = ref('')
  const errorBySchool = ref<Record<string, string>>({})

  const currentSchoolId = computed(() => userStore.profile?.schoolId ?? '')
  const currentWeather = computed(() => weatherBySchool.value[currentSchoolId.value] ?? null)
  const currentError = computed(() => errorBySchool.value[currentSchoolId.value] ?? '')
  const isLoading = computed(() => loadingSchoolId.value === currentSchoolId.value)

  async function loadForSchool(schoolId: string, force = false): Promise<SchoolWeatherData | null> {
    if (!schoolId) return null
    if (!force && attemptedBySchool.value[schoolId]) return weatherBySchool.value[schoolId] ?? null
    attemptedBySchool.value = { ...attemptedBySchool.value, [schoolId]: true }
    loadingSchoolId.value = schoolId
    errorBySchool.value = { ...errorBySchool.value, [schoolId]: '' }
    try {
      const weather = await getCurrentSchoolWeather()
      if (weather.schoolId === schoolId) {
        weatherBySchool.value = { ...weatherBySchool.value, [schoolId]: weather }
        return weather
      }
      return null
    } catch (error) {
      errorBySchool.value = {
        ...errorBySchool.value,
        [schoolId]: error instanceof Error ? error.message : '天气暂不可用',
      }
      return null
    } finally {
      if (loadingSchoolId.value === schoolId) loadingSchoolId.value = ''
    }
  }

  return {
    weatherBySchool,
    currentWeather,
    currentError,
    isLoading,
    loadForSchool,
  }
})
