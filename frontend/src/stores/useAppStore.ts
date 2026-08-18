import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { mockHistory, mockReviews, mockSchools, mockStores } from '../data/mock'
import type { HistoryAction, HistoryItem, ReviewItem, StoreItem } from '../types'

const EATEN_STORAGE_KEY = 'eat-anything:eaten-store-ids'
const FAVORITE_STORAGE_KEY = 'eat-anything:favorite-store-ids'
const SCHOOL_STORAGE_KEY = 'eat-anything:selected-school'
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

function loadStoreIds(storageKey: string) {
  try {
    const stored = uni.getStorageSync(storageKey)
    if (Array.isArray(stored)) return new Set(stored.map(Number))
  } catch {
    // Storage is optional in preview mode.
  }
  return null
}

function loadAreaMap() {
  try {
    const stored = uni.getStorageSync(AREA_STORAGE_KEY)
    if (stored && typeof stored === 'object') return { ...stored } as Record<string, string>
  } catch {
    // Use the first area when storage is unavailable.
  }
  return {} as Record<string, string>
}

export const useAppStore = defineStore('app', () => {
  const storedEatenIds = loadStoreIds(EATEN_STORAGE_KEY)
  const storedFavoriteIds = loadStoreIds(FAVORITE_STORAGE_KEY)
  const schools = ref(mockSchools.map((school) => ({ ...school, areas: school.areas.map((area) => ({ ...area })) })))
  const stores = ref<StoreItem[]>(mockStores.map((item) => ({
    ...item,
    eaten: storedEatenIds ? storedEatenIds.has(item.id) : item.eaten,
    favorite: storedFavoriteIds ? storedFavoriteIds.has(item.id) : item.favorite
  })))
  const reviews = ref<ReviewItem[]>(mockReviews.map((item) => ({ ...item })))
  const history = ref<HistoryItem[]>(mockHistory.map((item) => ({ ...item })))
  const areaBySchool = ref(loadAreaMap())
  const storedSchoolId = uni.getStorageSync(SCHOOL_STORAGE_KEY)
  const initialSchool = schools.value.find((school) => school.id === storedSchoolId) || schools.value[0]
  const selectedSchoolId = ref(initialSchool?.id || '')
  const selectedAreaId = ref(areaBySchool.value[selectedSchoolId.value] || initialSchool?.areas[0]?.id || '')
  const currentPick = ref<StoreItem | null>(null)
  const lockedPickId = ref<number | null>(null)
  const checkedInPickId = ref<number | null>(null)
  const fontPreference = ref<FontPreference>(loadFontPreference())
  applyFontPreferenceToHost(fontPreference.value)

  const activeSchool = computed(() => schools.value.find((school) => school.id === selectedSchoolId.value) || schools.value[0])
  const activeAreas = computed(() => activeSchool.value?.areas || [])
  const activeArea = computed(() => activeAreas.value.find((area) => area.id === selectedAreaId.value) || activeAreas.value[0])
  const activeSchoolStores = computed(() => stores.value.filter((store) => store.schoolId === activeSchool.value?.id))
  const activeAreaStores = computed(() => activeSchoolStores.value.filter((store) => store.areaId === activeArea.value?.id))
  const eatenStores = computed(() => stores.value.filter((item) => item.eaten))
  const favoriteStores = computed(() => stores.value.filter((item) => item.favorite))
  const activeSchoolEatenStores = computed(() => activeSchoolStores.value.filter((item) => item.eaten))
  const activeSchoolFavoriteStores = computed(() => activeSchoolStores.value.filter((item) => item.favorite))
  const isPickLocked = computed(() => lockedPickId.value !== null && currentPick.value?.id === lockedPickId.value)
  const isCurrentPickCheckedIn = computed(() => checkedInPickId.value !== null && currentPick.value?.id === checkedInPickId.value)
  const fontClass = computed(() => fontPreference.value === 'system' ? 'system-font' : 'cheese-font')

  function persistStoreState(key: string, ids: number[]) {
    try { uni.setStorageSync(key, ids) } catch { /* Keep session state when storage is unavailable. */ }
  }

  function clearPick() {
    currentPick.value = null
    lockedPickId.value = null
    checkedInPickId.value = null
  }

  function selectSchool(schoolId: string) {
    const school = schools.value.find((item) => item.id === schoolId)
    if (!school) return false
    selectedSchoolId.value = school.id
    selectedAreaId.value = areaBySchool.value[school.id] || school.areas[0]?.id || ''
    clearPick()
    uni.setStorageSync(SCHOOL_STORAGE_KEY, school.id)
    return true
  }

  function selectArea(areaId: string) {
    if (!activeAreas.value.some((area) => area.id === areaId)) return false
    selectedAreaId.value = areaId
    areaBySchool.value = { ...areaBySchool.value, [selectedSchoolId.value]: areaId }
    clearPick()
    uni.setStorageSync(AREA_STORAGE_KEY, areaBySchool.value)
    return true
  }

  function findStore(storeId: number) { return stores.value.find((item) => item.id === storeId) }
  function findArea(store: StoreItem | undefined) {
    if (!store) return undefined
    return schools.value.find((school) => school.id === store.schoolId)?.areas.find((area) => area.id === store.areaId)
  }

  function addHistory(storeId: number, action: HistoryAction) {
    const now = new Date()
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    history.value.unshift({ id: Date.now(), storeId, action, date: `今天 ${time}` })
  }

  function drawRandomStore() {
    if (isPickLocked.value) return currentPick.value
    const pool = activeAreaStores.value
    if (!pool.length) return null
    const candidates = currentPick.value && pool.length > 1 ? pool.filter((item) => item.id !== currentPick.value?.id) : pool
    const next = candidates[Math.floor(Math.random() * candidates.length)]
    currentPick.value = next
    lockedPickId.value = null
    checkedInPickId.value = null
    addHistory(next.id, '随机抽取')
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
    target.eaten = true
    persistStoreState(EATEN_STORAGE_KEY, eatenStores.value.map((item) => item.id))
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

  function toggleFavorite(storeId: number) {
    const target = findStore(storeId)
    if (target) {
      target.favorite = !target.favorite
      persistStoreState(FAVORITE_STORAGE_KEY, favoriteStores.value.map((item) => item.id))
      if (target.favorite) addHistory(target.id, '加入收藏')
    }
    return target?.favorite ?? false
  }

  function toggleEaten(storeId: number) {
    const target = findStore(storeId)
    if (target) {
      target.eaten = !target.eaten
      persistStoreState(EATEN_STORAGE_KEY, eatenStores.value.map((item) => item.id))
    }
    return target?.eaten ?? false
  }

  function recordVisit(storeId: number) { addHistory(storeId, '浏览店铺') }

  function setFontPreference(preference: FontPreference) {
    fontPreference.value = preference
    try { uni.setStorageSync(FONT_STORAGE_KEY, preference) } catch { /* Keep the session preference. */ }
    applyFontPreferenceToHost(preference)
  }

  function addReview(storeId: number, rating: number, content: string) {
    reviews.value.unshift({ id: Date.now(), storeId, rating, content, date: `${new Date().getMonth() + 1}月${new Date().getDate()}日` })
    addHistory(storeId, '提交评价')
  }

  return {
    schools, stores, reviews, history, selectedSchoolId, selectedAreaId, activeSchool, activeAreas, activeArea,
    activeSchoolStores, activeAreaStores, activeSchoolEatenStores, activeSchoolFavoriteStores, currentPick,
    isPickLocked, isCurrentPickCheckedIn, eatenStores, favoriteStores, selectSchool, selectArea, findStore,
    findArea, drawRandomStore, lockCurrentPick, checkInCurrentPick, unlockCurrentPick, continueAfterCheckIn,
    toggleFavorite, toggleEaten, recordVisit, addReview, fontPreference, fontClass, setFontPreference
  }
})
