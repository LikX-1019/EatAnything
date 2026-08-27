import { clearAdminAccessToken, getAdminAccessToken, setAdminAccessToken } from '@/auth/admin-token'
import { del, get, patch, post, uploadFile, type RequestHeaders } from './client'
import type { PageData } from './stores'

export interface AdminAuthData { accessToken: string; tokenType: string; expiresIn: number; admin: { id: string; username: string; displayName: string; roles: string[] } }
export interface AdminStore { id: string; storeCode: string; schoolId: string; schoolCode: string; schoolName: string; areaId: string; areaCode: string; name: string; category: string; address: string; area: string; imageUrl?: string | null; status: 'active' | 'hidden' | 'closed'; score?: number | null; reviewCount: number; version: number; createdAt: string; updatedAt: string }
export interface AdminStoreInput { storeCode: string; schoolId: number; areaId: number; name: string; category: string; address: string; imageUrl?: string | null; status?: 'active' | 'hidden' | 'closed' }
export interface AdminStoreUpdate extends Partial<Omit<AdminStoreInput, 'storeCode'>> { version: number }
export interface StoreImportResult { totalRows: number; createdCount: number; updatedCount: number; items: Array<{ row: number; storeCode: string; storeId: string; action: string }> }
export interface AdminSchoolOption { id: string; schoolCode: string; name: string; areas: Array<{ id: string; areaCode: string; name: string }> }

function authOptions(): { auth: false; headers: RequestHeaders; skipAuthRefresh: true } { const token = getAdminAccessToken(); return { auth: false, headers: token ? { Authorization: `Bearer ${token}` } : {}, skipAuthRefresh: true } }

export async function adminLogin(username: string, password: string): Promise<AdminAuthData> {
  const data = await post<AdminAuthData, { username: string; password: string }>('/admin/auth/login', { username, password }, { auth: false, skipAuthRefresh: true })
  setAdminAccessToken(data.accessToken)
  return data
}

export function adminLogout(): void { clearAdminAccessToken() }
export function hasAdminSession(): boolean { return Boolean(getAdminAccessToken()) }
export function getAdminStores(params: { keyword?: string; status?: string; page?: number; pageSize?: number } = {}): Promise<PageData<AdminStore>> {
  return get<PageData<AdminStore>, Record<string, string | number>>('/admin/stores', { ...params, page: params.page ?? 1, page_size: params.pageSize ?? 20 }, authOptions())
}
export function getAdminStoreOptions(): Promise<{ schools: AdminSchoolOption[] }> { return get<{ schools: AdminSchoolOption[] }>('/admin/stores/options', undefined, authOptions()) }
export function createAdminStore(payload: AdminStoreInput): Promise<AdminStore> { return post<AdminStore, AdminStoreInput>('/admin/stores', payload, authOptions()) }
export function updateAdminStore(storeId: string, payload: AdminStoreUpdate): Promise<AdminStore> { return patch<AdminStore, AdminStoreUpdate>(`/admin/stores/${encodeURIComponent(storeId)}`, payload, authOptions()) }
export function deleteAdminStore(store: AdminStore): Promise<void> { return del<void>(`/admin/stores/${encodeURIComponent(store.id)}?version=${store.version}`, authOptions()) }
export function importAdminStores(filePath: string): Promise<StoreImportResult> { return uploadFile<StoreImportResult>('/admin/stores/import', filePath, undefined, authOptions().headers, { auth: false, skipAuthRefresh: true }) }
export function uploadAdminImage(filePath: string): Promise<{ url: string; contentType: string; size: number }> { return uploadFile('/admin/uploads/images', filePath, undefined, authOptions().headers, { auth: false, skipAuthRefresh: true }) }
