<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { computed, reactive, ref } from 'vue'
import { adminLogout, createAdminStore, deleteAdminStore, getAdminStoreOptions, getAdminStores, hasAdminSession, importAdminStores, updateAdminStore, uploadAdminImage, type AdminSchoolOption, type AdminStore } from '../../api/admin'
import { ApiClientError } from '../../api/types'

const stores = ref<AdminStore[]>([])
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const status = ref('')
const page = ref(1)
const total = ref(0)
const schools = ref<AdminSchoolOption[]>([])
const editingId = ref<string | null>(null)
const form = reactive({ storeCode: '', schoolId: '', areaId: '', name: '', category: '', address: '', imageUrl: '', status: 'hidden' as 'active' | 'hidden' | 'closed', version: 1 })
const editing = computed(() => Boolean(editingId.value))
type PickerEvent = { detail: { value: number } }

function resetForm() { editingId.value = null; Object.assign(form, { storeCode: '', schoolId: '', areaId: '', name: '', category: '', address: '', imageUrl: '', status: 'hidden', version: 1 }) }
async function load() {
  if (!hasAdminSession()) return uni.redirectTo({ url: '/pages/admin/login' })
  loading.value = true; errorMessage.value = ''
  try { const [data, options] = await Promise.all([getAdminStores({ keyword: keyword.value, status: status.value, page: page.value }), schools.value.length ? Promise.resolve({ schools: schools.value }) : getAdminStoreOptions()]); stores.value = data.items; total.value = data.total; schools.value = options.schools }
  catch (error) { if (error instanceof ApiClientError && error.status === 401) { adminLogout(); return uni.redirectTo({ url: '/pages/admin/login' }) }; errorMessage.value = error instanceof ApiClientError ? error.message : '店铺加载失败' }
  finally { loading.value = false }
}
function edit(store: AdminStore) { editingId.value = store.id; Object.assign(form, { storeCode: store.storeCode, schoolId: store.schoolId, areaId: store.areaId, name: store.name, category: store.category, address: store.address, imageUrl: store.imageUrl ?? '', status: store.status, version: store.version }) }
async function save() {
  const required = [form.schoolId, form.areaId, form.name, form.category, form.address]
  if (!form.storeCode.trim() || required.some((value) => !String(value).trim())) return uni.showToast({ title: '请完整填写店铺信息', icon: 'none' })
  try {
    if (editingId.value) await updateAdminStore(editingId.value, { version: form.version, schoolId: Number(form.schoolId), areaId: Number(form.areaId), name: form.name, category: form.category, address: form.address, imageUrl: form.imageUrl || null, status: form.status })
    else await createAdminStore({ storeCode: form.storeCode, schoolId: Number(form.schoolId), areaId: Number(form.areaId), name: form.name, category: form.category, address: form.address, imageUrl: form.imageUrl || null, status: form.status })
    uni.showToast({ title: '已保存', icon: 'success' }); resetForm(); await load()
  } catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '保存失败', icon: 'none' }) }
}
async function archive(store: AdminStore) { const result = await uni.showModal({ title: '确认删除', content: `将“${store.name}”下架并保留历史记录？` }); if (!result.confirm) return; try { await deleteAdminStore(store); await load() } catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '操作失败', icon: 'none' }) } }
async function chooseImage() { const result = await new Promise<string | null>((resolve) => uni.chooseImage({ count: 1, sizeType: ['compressed'], success: (value) => resolve(value.tempFilePaths[0] ?? null), fail: () => resolve(null) })); if (!result) return; try { const image = await uploadAdminImage(result); form.imageUrl = image.url } catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '图片上传失败', icon: 'none' }) } }
async function chooseImport() { const chooser = (uni as unknown as { chooseFile?: (options: { count: number; success: (result: { tempFilePaths: string[] }) => void; fail: () => void }) => void }).chooseFile; if (!chooser) return uni.showToast({ title: '当前平台不支持文件导入，请使用 H5 管理端', icon: 'none' }); chooser({ count: 1, success: async (result) => { try { const data = await importAdminStores(result.tempFilePaths[0]); uni.showToast({ title: `导入完成：${data.totalRows} 行`, icon: 'success' }); await load() } catch (error) { uni.showToast({ title: error instanceof ApiClientError ? error.message : '导入失败', icon: 'none' }) } }, fail: () => undefined }) }
function logout() { adminLogout(); uni.redirectTo({ url: '/pages/admin/login' }) }
function setStatus(event: PickerEvent) { status.value = ['', 'active', 'hidden', 'closed'][event.detail.value] ?? ''; page.value = 1; void load() }
function setFormStatus(event: PickerEvent) { form.status = ['active', 'hidden', 'closed'][event.detail.value] as typeof form.status }
const selectedSchool = computed(() => schools.value.find((school) => school.id === form.schoolId) ?? null)
function setSchool(event: PickerEvent) { form.schoolId = selectedSchoolOptions.value[event.detail.value]?.id ?? ''; form.areaId = '' }
const selectedSchoolOptions = computed(() => schools.value)
function setArea(event: PickerEvent) { form.areaId = selectedSchool.value?.areas[event.detail.value]?.id ?? '' }
onShow(() => { void load() })
</script>

<template>
  <view class="admin-page"><view class="toolbar"><text class="title">店铺管理</text><view><button size="mini" @tap="chooseImport">批量导入</button><button size="mini" @tap="logout">退出</button></view></view>
    <view class="filters"><input v-model="keyword" placeholder="搜索店铺" /><picker :range="['全部','active','hidden','closed']" @change="setStatus"><view class="picker">状态：{{ status || '全部' }}</view></picker><button size="mini" @tap="load">搜索</button></view>
    <view v-if="loading" class="state">加载中…</view><view v-else-if="errorMessage" class="state"><text>{{ errorMessage }}</text><button size="mini" @tap="load">重试</button></view><view v-else-if="!stores.length" class="state">暂无店铺</view>
    <view v-else class="list"><view v-for="store in stores" :key="store.id" class="item"><view class="item-copy"><text class="name">{{ store.name }}</text><text>{{ store.storeCode }} · {{ store.status }} · v{{ store.version }}</text><text>{{ store.address }}</text></view><view><button size="mini" @tap="edit(store)">编辑</button><button size="mini" @tap="archive(store)">下架</button></view></view></view>
    <view class="editor"><text class="section-title">{{ editing ? '编辑店铺' : '新增店铺' }}</text><input v-model="form.storeCode" :disabled="editing" placeholder="店铺编码" /><picker :range="schools.map((school) => school.name)" @change="setSchool"><view class="picker">学校：{{ selectedSchool?.name || '请选择学校' }}</view></picker><picker :range="selectedSchool?.areas.map((area) => area.name) || []" @change="setArea"><view class="picker">区域：{{ selectedSchool?.areas.find((area) => area.id === form.areaId)?.name || '请选择区域' }}</view></picker><input v-model="form.name" placeholder="店铺名称" /><input v-model="form.category" placeholder="分类" /><input v-model="form.address" placeholder="地址" /><input v-model="form.imageUrl" placeholder="图片 URL（可选）" /><picker :range="['active','hidden','closed']" @change="setFormStatus"><view class="picker">状态：{{ form.status }}</view></picker><view><button class="primary" @tap="save">保存</button><button v-if="editing" @tap="resetForm">取消编辑</button><button @tap="chooseImage">上传图片</button></view></view>
  </view>
</template>

<style scoped>
.admin-page { min-height: 100vh; padding: 24rpx; background: #f4f6f8; }.toolbar,.filters,.item,.toolbar > view { display: flex; align-items: center; }.toolbar { justify-content: space-between; }.title { color: #203040; font-size: 38rpx; font-weight: 800; }.toolbar button,.item button { margin-left: 10rpx; }.filters { gap: 12rpx; margin: 20rpx 0; }.filters input { flex: 1; height: 68rpx; padding: 0 15rpx; background: #fff; }.picker { padding: 17rpx; background: #fff; color: #526273; }.state { padding: 80rpx 0; color: #718090; text-align: center; }.list { display: flex; flex-direction: column; gap: 12rpx; }.item { justify-content: space-between; padding: 20rpx; border-radius: 12rpx; background: #fff; }.item-copy { display: flex; min-width: 0; flex-direction: column; gap: 7rpx; color: #718090; font-size: 22rpx; }.name,.section-title { color: #203040; font-size: 29rpx; font-weight: 800; }.editor { margin-top: 24rpx; padding: 22rpx; border-radius: 12rpx; background: #fff; }.editor input { height: 70rpx; margin-top: 12rpx; padding: 0 15rpx; border: 1rpx solid #d6dde5; }.editor .picker { margin-top: 12rpx; }.editor button { margin: 18rpx 8rpx 0 0; }.primary { background: #2f6fed; color: #fff; }
</style>
