import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getStores, randomStore } from '@/api/stores'
import { mockHistory, mockReviews } from '@/data/mock'
import type { HistoryAction, HistoryItem, ReviewItem, StoreArea, StoreItem } from '@/types'
import { useUserStore } from './useUserStore'

const AREA_STORAGE_KEY = 'eat-anything:area-by-school'
const FONT_STORAGE_KEY = 'eat-anything:font-preference'
type FontPreference = 'cheese' | 'system'

function loadFontPreference(): FontPreference {
  try { return uni.getStorageSync(FONT_STORAGE_KEY) === 'system' ? 'system' : 'cheese' } catch { return 'cheese' }
}

function applyFontPreferenceToHost(preference: FontPreference) {
  // #ifdef H5
  if (typeof document !== 'undefined') document.documentElement.dataset.appFont = preference
  // #endif
}

function loadAreaMap(): Record<string, string> {
  try {
    const stored: unknown = uni.getStorageSync(AREA_STORAGE_KEY)
    if (stored && typeof stored === 'object' && !Array.isArray(stored)) {
      return { ...stored } as Record<string, string>
    }
  } catch {
    // Use the first real store area when storage is unavailable.
  }
  return {}
}

export const useAppStore = defineStore('app', () => {
  const userStore = useUserStore()
  const stores = ref<StoreItem[]>([])
  const reviews = ref<ReviewItem[]>(mockReviews.map((item) => ({ ...item })))
  const history = ref<HistoryItem[]>(mockHistory.map((item) => ({ ...item })))
  const areaBySchool = ref(loadAreaMap())
  const selectedAreaId = ref('')
  const currentPick = ref<StoreItem | null>(null)
  const lockedPickId = ref<string | null>(null)
  const checkedInPickId = ref<string | null>(null)
  const storesLoaded = ref(false)
  const fontPreference = ref<FontPreference>(loadFontPreference())
  let storesPromise: Promise<void> | null = null
  applyFontPreferenceToHost(fontPreference.value)

  const activeSchool = computed(() => userStore.currentSchool)
  const activeSchoolStores = computed(() => {
    const schoolId = userStore.profile?.schoolId
    return schoolId ? stores.value.filter((store) => store.schoolId === schoolId) : []
  })
  const activeAreas = computed<StoreArea[]>(() => {
    const uniqueAreas = new Set<string>()
    for (const store of activeSchoolStores.value) {
      const area = store.area.trim()
      if (area) uniqueAreas.add(area)
    }
    return [...uniqueAreas].map((area) => ({ id: area, name: area }))
  })
  const activeArea = computed(() => activeAreas.value.find((area) => area.id === selectedAreaId.value) ?? activeAreas.value[0])
  const activeAreaStores = computed(() => {
    const area = activeArea.value?.name
    return area ? activeSchoolStores.value.filter((store) => store.area.trim() === area) : []
  })
  const eatenStores = computed(() => stores.value.filter((item) => item.isEaten))
  const favoriteStores = computed(() => stores.value.filter((item) => item.isFavorite))
  const activeSchoolEatenStores = computed(() => activeSchoolStores.value.filter((item) => item.isEaten))
  const activeSchoolFavoriteStores = computed(() => activeSchoolStores.value.filter((item) => item.isFavorite))
  const isPickLocked = computed(() => lockedPickId.value !== null && currentPick.value?.id === lockedPickId.value)
  const isCurrentPickCheckedIn = computed(() => checkedInPickId.value !== null && currentPick.value?.id === checkedInPickId.value)
  const fontClass = computed(() => fontPreference.value === 'system' ? 'system-font' : 'cheese-font')

  function clearPick() {
    currentPick.value = null
    lockedPickId.value = null
    checkedInPickId.value = null
  }

  function restoreAreaSelection() {
    const schoolId = userStore.profile?.schoolId
    const rememberedArea = schoolId ? areaBySchool.value[schoolId] : ''
    selectedAreaId.value = activeAreas.value.some((area) => area.id === rememberedArea)
      ? rememberedArea
      : activeAreas.value[0]?.id || ''
  }

  async function loadStores(force = false): Promise<void> {
    if (storesLoaded.value && !force) return

    if (!storesPromise) {
      storesPromise = (async () => {
        const page = await getStores({ page: 1, pageSize: 100 })
        stores.value = page.items
        storesLoaded.value = true
        restoreAreaSelection()
      })().finally(() => {
        storesPromise = null
      })
    }

    await storesPromise
  }

  async function initialize(): Promise<void> {
    await userStore.initialize()
    await loadStores()
  }

  async function reloadForSchool(): Promise<void> {
    selectedAreaId.value = ''
    clearPick()
    await loadStores(true)
  }

  function selectArea(areaId: string): boolean {
    if (!activeAreas.value.some((area) => area.id === areaId)) return false
    selectedAreaId.value = areaId
    const schoolId = userStore.profile?.schoolId
    if (schoolId) {
      areaBySchool.value = { ...areaBySchool.value, [schoolId]: areaId }
      try { uni.setStorageSync(AREA_STORAGE_KEY, areaBySchool.value) } catch { /* Keep the selection for this session. */ }
    }
    clearPick()
    return true
  }

  function findStore(storeId: string | number): StoreItem | undefined {
    return stores.value.find((item) => item.id === String(storeId))
  }

  function findArea(store: StoreItem | undefined): StoreArea | undefined {
    const area = store?.area.trim()
    return area ? { id: area, name: area } : undefined
  }

  function addHistory(storeId: string | number, action: HistoryAction) {
    const now = new Date()
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    history.value.unshift({ id: Date.now(), storeId, action, date: `今天 ${time}` })
  }

  async function drawRandomStore(): Promise<StoreItem> {
    const result = await randomStore(currentPick.value?.id)
    const next = result.store
    const existingIndex = stores.value.findIndex((store) => store.id === next.id)
    if (existingIndex >= 0) stores.value.splice(existingIndex, 1, next)
    else stores.value.unshift(next)
    currentPick.value = next
    lockedPickId.value = null
    checkedInPickId.value = null
    return next
  }

  function lockCurrentPick() {
    if (!currentPick.value) return false
    lockedPickId.value = currentPick.value.id
    checkedInPickId.value = null
    addHistory(currentPick.value.id, '锁定选择')
    return true
  }

  function checkInCurrentPick() {
    if (!currentPick.value || !isPickLocked.value) return false
    const target = findStore(currentPick.value.id)
    if (!target) return false
    target.isEaten = true
    if (checkedInPickId.value !== target.id) {
      addHistory(target.id, '到店打卡')
      checkedInPickId.value = target.id
    }
    return true
  }

  function unlockCurrentPick() {
    if (!isPickLocked.value || isCurrentPickCheckedIn.value) return false
    lockedPickId.value = null
    checkedInPickId.value = null
    return true
  }

  function continueAfterCheckIn() { clearPick() }

  function toggleFavorite(storeId: string) {
    const target = findStore(storeId)
    if (target) {
      target.isFavorite = !target.isFavorite
      if (target.isFavorite) addHistory(target.id, '加入收藏')
    }
    return target?.isFavorite ?? false
  }

  function toggleEaten(storeId: string) {
    const target = findStore(storeId)
    if (target) target.isEaten = !target.isEaten
    return target?.isEaten ?? false
  }

  function recordVisit(storeId: string) { addHistory(storeId, '浏览店铺') }

  function setFontPreference(preference: FontPreference) {
    fontPreference.value = preference
    try { uni.setStorageSync(FONT_STORAGE_KEY, preference) } catch { /* Keep the session preference. */ }
    applyFontPreferenceToHost(preference)
  }

  function addReview(storeId: string, rating: number, content: string) {
    reviews.value.unshift({ id: Date.now(), storeId, rating, content, date: `${new Date().getMonth() + 1}月${new Date().getDate()}日` })
    addHistory(storeId, '提交评价')
  }

  return {
    stores, reviews, history, selectedAreaId, activeSchool, activeAreas, activeArea,
    activeSchoolStores, activeAreaStores, activeSchoolEatenStores, activeSchoolFavoriteStores, currentPick,
    isPickLocked, isCurrentPickCheckedIn, eatenStores, favoriteStores, storesLoaded, initialize, loadStores,
    reloadForSchool, selectArea, findStore, findArea, drawRandomStore, lockCurrentPick, checkInCurrentPick,
    unlockCurrentPick, continueAfterCheckIn, toggleFavorite, toggleEaten, recordVisit, addReview,
    fontPreference, fontClass, setFontPreference,
  }
})
