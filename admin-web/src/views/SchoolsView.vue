<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import StatusSticker from '../components/StatusSticker.vue'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore, type SchoolOption } from '../stores/workspace'

const auth = useAuthStore(); const workspace = useWorkspaceStore()
const loading = ref(false); const dialog = ref(false); const areaDialog = ref(false); const editingId = ref(''); const selectedSchool = ref<SchoolOption | null>(null)
const form = reactive({ schoolCode: '', name: '', city: '', district: '', address: '', latitude: '', longitude: '', status: 'active' })
const areaForm = reactive({ areaCode: '', name: '', description: '', sortOrder: 0, status: 'active' })
async function load() { loading.value = true; try { await workspace.loadSchools() } finally { loading.value = false } }
function openCreate() { editingId.value=''; Object.assign(form,{schoolCode:'',name:'',city:'',district:'',address:'',latitude:'',longitude:'',status:'active'}); dialog.value=true }
function openEdit(item: SchoolOption) { editingId.value=item.id; Object.assign(form,{schoolCode:item.schoolCode,name:item.name,city:item.city||'',district:item.district||'',address:item.address||'',latitude:item.latitude==null?'':String(item.latitude),longitude:item.longitude==null?'':String(item.longitude),status:item.status}); dialog.value=true }
async function save() {
  const hasLatitude = form.latitude.trim() !== ''
  const hasLongitude = form.longitude.trim() !== ''
  if (hasLatitude !== hasLongitude) return ElMessage.warning('经纬度必须同时填写或同时清空')
  const latitude = hasLatitude ? Number(form.latitude) : null
  const longitude = hasLongitude ? Number(form.longitude) : null
  if (latitude !== null && (!Number.isFinite(latitude) || latitude < -90 || latitude > 90)) return ElMessage.warning('纬度必须介于 -90 到 90')
  if (longitude !== null && (!Number.isFinite(longitude) || longitude < -180 || longitude > 180)) return ElMessage.warning('经度必须介于 -180 到 180')
  const payload = { ...form, latitude, longitude }
  try { if(editingId.value) await api.patch(`/admin/schools/${editingId.value}`,payload); else await api.post('/admin/schools',payload); ElMessage.success('学校资料已保存'); dialog.value=false; await load() } catch(e){ ElMessage.error(e instanceof Error?e.message:'保存失败') }
}
function openArea(item: SchoolOption) { selectedSchool.value=item; Object.assign(areaForm,{areaCode:'',name:'',description:'',sortOrder:0,status:'active'}); areaDialog.value=true }
async function saveArea(){ if(!selectedSchool.value)return; try{await api.post(`/admin/schools/${selectedSchool.value.id}/areas`,areaForm);ElMessage.success('区域已添加');areaDialog.value=false;await load()}catch(e){ElMessage.error(e instanceof Error?e.message:'保存失败')} }
onMounted(load)
</script>
<template>
  <section class="paper-card table-paper">
    <div class="table-toolbar"><h3>学校档案册</h3><el-button v-if="auth.admin?.isPlatformAdmin" type="primary" @click="openCreate">＋ 新增学校</el-button></div>
    <el-table v-loading="loading" :data="workspace.schools" row-key="id"><el-table-column prop="schoolCode" label="学校编码" width="150"><template #default="s"><span class="mono">{{ s.row.schoolCode }}</span></template></el-table-column><el-table-column prop="name" label="学校名称" min-width="190" /><el-table-column prop="city" label="城市" width="110" /><el-table-column label="天气坐标" width="190"><template #default="s"><span v-if="s.row.latitude!=null&&s.row.longitude!=null" class="mono">{{ s.row.latitude }}, {{ s.row.longitude }}</span><span v-else>未配置</span></template></el-table-column><el-table-column prop="storeCount" label="店铺" width="80" /><el-table-column prop="userCount" label="用户" width="80" /><el-table-column label="状态" width="100"><template #default="s"><StatusSticker :status="s.row.status" /></template></el-table-column><el-table-column label="操作" width="210" fixed="right"><template #default="s"><el-button link type="primary" @click="openEdit(s.row)">编辑</el-button><el-button link type="success" @click="openArea(s.row)">添加区域</el-button></template></el-table-column><el-table-column type="expand"><template #default="s"><div class="detail-list"><template v-for="area in s.row.areas" :key="area.id"><dt>{{ area.areaCode }}</dt><dd>{{ area.name }} · {{ area.status }}</dd></template><template v-if="!s.row.areas.length"><dt>区域</dt><dd>尚未添加区域</dd></template></div></template></el-table-column></el-table>
  </section>
  <el-dialog v-model="dialog" :title="editingId?'编辑学校贴纸':'新增学校贴纸'" width="600px"><el-form label-position="top"><div class="form-grid"><el-form-item label="学校编码"><el-input v-model="form.schoolCode" :disabled="Boolean(editingId)" /></el-form-item><el-form-item label="学校名称"><el-input v-model="form.name" /></el-form-item><el-form-item label="城市"><el-input v-model="form.city" /></el-form-item><el-form-item label="区县"><el-input v-model="form.district" /></el-form-item><el-form-item label="地址" class="wide"><el-input v-model="form.address" /></el-form-item><el-form-item label="纬度（WGS84）"><el-input v-model="form.latitude" inputmode="decimal" placeholder="例如 30.460717" /></el-form-item><el-form-item label="经度（WGS84）"><el-input v-model="form.longitude" inputmode="decimal" placeholder="例如 114.268004" /></el-form-item><el-form-item label="状态"><el-select v-model="form.status"><el-option label="启用" value="active"/><el-option label="停用" value="hidden"/></el-select></el-form-item></div></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template></el-dialog>
  <el-dialog v-model="areaDialog" title="贴一张新区域标签" width="560px"><el-form label-position="top"><div class="form-grid"><el-form-item label="区域编码"><el-input v-model="areaForm.areaCode" /></el-form-item><el-form-item label="区域名称"><el-input v-model="areaForm.name" /></el-form-item><el-form-item label="排序"><el-input-number v-model="areaForm.sortOrder" :min="0" /></el-form-item><el-form-item label="状态"><el-select v-model="areaForm.status"><el-option label="启用" value="active"/><el-option label="停用" value="hidden"/></el-select></el-form-item><el-form-item label="描述" class="wide"><el-input v-model="areaForm.description" type="textarea" /></el-form-item></div></el-form><template #footer><el-button @click="areaDialog=false">取消</el-button><el-button type="primary" @click="saveArea">保存</el-button></template></el-dialog>
</template>
