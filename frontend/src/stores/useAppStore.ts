import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getStoreDetail, getStores, randomStore, recordStoreVisit, type StoreDetail } from '@/api/stores'
import { createCheckIn as createCheckInRequest } from '@/api/checkins'
import { getFavorites, addFavorite, removeFavorite, getEaten } from '@/api/states'
import { getHistory, type HistoryRecord } from '@/api/history'
import type { StoreArea, StoreItem } from '@/types'
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
  const history = ref<HistoryRecord[]>([])
  const areaBySchool = ref(loadAreaMap())
  const selectedAreaId = ref('')
  const currentPick = ref<StoreItem | null>(null)
  const lockedPickId = ref<string | null>(null)
  const checkedInPickId = ref<string | null>(null)
  const storesLoaded = ref(false)
  const behaviorLoaded = ref(false)
  const fontPreference = ref<FontPreference>(loadFontPreference())
  let storesPromise: Promise<void> | null = null
  let behaviorPromise: Promise<void> | null = null
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
        const firstPage = await getStores({ page: 1, pageSize: 100 })
        const items = [...firstPage.items]
        for (let page = 2; items.length < firstPage.total; page += 1) {
          const nextPage = await getStores({ page, pageSize: 100 })
          if (!nextPage.items.length) break
          items.push(...nextPage.items)
        }
        stores.value = items
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
    if (!behaviorLoaded.value && !behaviorPromise) {
      behaviorPromise = (async () => {
        await loadStores()
        await Promise.all([loadFavorites(), loadEaten(), loadHistory()])
        behaviorLoaded.value = true
      })().finally(() => {
        behaviorPromise = null
      })
    }
    await behaviorPromise
  }

  async function reloadForSchool(): Promise<void> {
    selectedAreaId.value = ''
    clearPick()
    await loadStores(true)
    await Promise.all([loadFavorites(), loadEaten()])
    behaviorLoaded.value = true
  }

  async function refresh(): Promise<void> {
    await userStore.initialize()
    await userStore.refreshProfile()
    await loadStores(true)
    await Promise.all([loadFavorites(), loadEaten(), loadHistory()])
    behaviorLoaded.value = true
  }

  function patchStoreState(storeId: string, patch: Partial<Pick<StoreItem, 'isFavorite' | 'isEaten'>>): void {
    const target = findStore(storeId)
    if (target) Object.assign(target, patch)
  }

  function mergeStores(items: StoreItem[]): void {
    for (const item of items) {
      const existingIndex = stores.value.findIndex((store) => store.id === item.id)
      if (existingIndex >= 0) stores.value.splice(existingIndex, 1, { ...stores.value[existingIndex], ...item })
      else stores.value.push(item)
    }
  }

  async function loadFavorites(): Promise<void> {
    const firstPage = await getFavorites({ page: 1, pageSize: 100 })
    const items = [...firstPage.items]
    for (let page = 2; items.length < firstPage.total; page += 1) {
      const nextPage = await getFavorites({ page, pageSize: 100 })
      if (!nextPage.items.length) break
      items.push(...nextPage.items)
    }
    mergeStores(items.map((store) => ({ ...store, isFavorite: true })))
    const favoriteIds = new Set(items.map((store) => store.id))
    const schoolId = userStore.profile?.schoolId
    for (const store of stores.value) {
      if (store.schoolId === schoolId && !favoriteIds.has(store.id)) store.isFavorite = false
    }
  }

  async function loadEaten(): Promise<void> {
    const firstPage = await getEaten({ page: 1, pageSize: 100 })
    const items = [...firstPage.items]
    for (let page = 2; items.length < firstPage.total; page += 1) {
      const nextPage = await getEaten({ page, pageSize: 100 })
      if (!nextPage.items.length) break
      items.push(...nextPage.items)
    }
    mergeStores(items.map((store) => ({ ...store, isEaten: true })))
    const eatenIds = new Set(items.map((store) => store.id))
    const schoolId = userStore.profile?.schoolId
    for (const store of stores.value) {
      if (store.schoolId === schoolId && !eatenIds.has(store.id)) store.isEaten = false
    }
  }

  async function loadHistory(): Promise<void> {
    const firstPage = await getHistory(1, 100)
    const items = [...firstPage.items]
    for (let page = 2; items.length < firstPage.total; page += 1) {
      const nextPage = await getHistory(page, 100)
      if (!nextPage.items.length) break
      items.push(...nextPage.items)
    }
    history.value = items
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
    return true
  }

  function unlockCurrentPick() {
    if (!isPickLocked.value || isCurrentPickCheckedIn.value) return false
    lockedPickId.value = null
    checkedInPickId.value = null
    return true
  }

  function continueAfterCheckIn() { clearPick() }

  const favoritePromises = new Map<string, Promise<boolean>>()

  async function toggleFavorite(storeId: string): Promise<boolean> {
    const pending = favoritePromises.get(storeId)
    if (pending) return pending

    const operation = toggleFavoriteInternal(storeId).finally(() => {
      if (favoritePromises.get(storeId) === operation) favoritePromises.delete(storeId)
    })
    favoritePromises.set(storeId, operation)
    return operation
  }

  async function toggleFavoriteInternal(storeId: string): Promise<boolean> {
    const target = findStore(storeId)
    if (!target) return false
    const nextValue = !target.isFavorite
    const result = nextValue ? await addFavorite(storeId) : await removeFavorite(storeId)
    patchStoreState(storeId, { isFavorite: result.isFavorite })
    await refreshProfileAfterWrite()
    return result.isFavorite
  }

  async function createCheckIn(storeId: string, filePath: string, note?: string): Promise<void> {
    await createCheckInRequest(storeId, filePath, note)
    patchStoreState(storeId, { isEaten: true })
    await refreshProfileAfterWrite()
  }

  async function refreshProfileAfterWrite(): Promise<void> {
    try {
      await userStore.refreshProfile()
    } catch {
      // The behavior write already succeeded; refresh the counters again when Profile opens.
    }
  }

  async function refreshStore(storeId: string): Promise<StoreDetail> {
    const detail = await getStoreDetail(storeId)
    mergeStores([detail])
    if (currentPick.value?.id === detail.id) currentPick.value = detail
    return detail
  }

  async function recordVisit(storeId: string): Promise<void> {
    try {
      await recordStoreVisit(storeId)
      await loadHistory()
    } catch {
      // Visit history is secondary to opening a store detail page.
    }
  }

  function setFontPreference(preference: FontPreference) {
    fontPreference.value = preference
    try { uni.setStorageSync(FONT_STORAGE_KEY, preference) } catch { /* Keep the session preference. */ }
    applyFontPreferenceToHost(preference)
  }

  return {
    stores, history, selectedAreaId, activeSchool, activeAreas, activeArea,
    activeSchoolStores, activeAreaStores, activeSchoolEatenStores, activeSchoolFavoriteStores, currentPick,
    isPickLocked, isCurrentPickCheckedIn, eatenStores, favoriteStores, storesLoaded, initialize, loadStores,
    reloadForSchool, refresh, selectArea, findStore, findArea, drawRandomStore, lockCurrentPick,
    unlockCurrentPick, continueAfterCheckIn, patchStoreState, toggleFavorite, createCheckIn, refreshStore, recordVisit,
    fontPreference, fontClass, setFontPreference,
  }
})
