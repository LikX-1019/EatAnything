<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

const props = defineProps<{ modelValue:string; mediaIds:string[] }>()
const emit = defineEmits<{ 'update:modelValue':[value:string]; 'update:mediaIds':[value:string[]] }>()
const editor = useEditor({
  content: props.modelValue || '<p></p>',
  extensions: [StarterKit.configure({ heading: { levels: [2, 3] } }), Image.configure({ inline: false })],
  onUpdate: ({ editor }) => emit('update:modelValue', editor.getHTML()),
})
watch(() => props.modelValue, value => {
  if (editor.value && value !== editor.value.getHTML()) editor.value.commands.setContent(value || '<p></p>', { emitUpdate: false })
})
onBeforeUnmount(() => editor.value?.destroy())

async function upload(event:Event){
  const input=event.target as HTMLInputElement;const file=input.files?.[0];input.value='';if(!file)return
  const data=new FormData();data.append('file',file)
  try{
    const result=await api.post<{mediaId:string;url:string}>('/admin/messages/images',data)
    editor.value?.chain().focus().setImage({src:result.url,alt:file.name}).run()
    emit('update:mediaIds',[...new Set([...props.mediaIds,result.mediaId])])
  }catch(error){ElMessage.error(error instanceof Error?error.message:'图片上传失败')}
}
</script>

<template>
  <div class="rich-editor">
    <div class="editor-toolbar" v-if="editor">
      <el-button size="small" :type="editor.isActive('bold')?'primary':''" @click="editor.chain().focus().toggleBold().run()">粗体</el-button>
      <el-button size="small" :type="editor.isActive('italic')?'primary':''" @click="editor.chain().focus().toggleItalic().run()">斜体</el-button>
      <el-button size="small" @click="editor.chain().focus().toggleHeading({level:2}).run()">二级标题</el-button>
      <el-button size="small" @click="editor.chain().focus().toggleBulletList().run()">无序列表</el-button>
      <el-button size="small" @click="editor.chain().focus().toggleOrderedList().run()">有序列表</el-button>
      <el-button size="small" @click="editor.chain().focus().toggleBlockquote().run()">引用</el-button>
      <label class="upload-button">插入图片<input type="file" accept="image/jpeg,image/png,image/webp" @change="upload"></label>
    </div>
    <EditorContent :editor="editor" class="editor-content" />
  </div>
</template>

<style scoped>
.rich-editor{overflow:hidden;border:1px solid #dcc6a8;border-radius:8px;background:#fffdf6}.editor-toolbar{display:flex;flex-wrap:wrap;gap:7px;padding:10px;border-bottom:1px dashed #dcc6a8}.editor-toolbar :deep(.el-button){margin-left:0}.upload-button{display:inline-flex;align-items:center;height:24px;padding:0 9px;border:1px solid #dcdfe6;border-radius:4px;background:#fff;cursor:pointer;font-size:12px}.upload-button input{display:none}.editor-content{min-height:260px;padding:14px 18px}.editor-content :deep(.tiptap){min-height:230px;outline:none;line-height:1.7}.editor-content :deep(img){display:block;max-width:100%;max-height:420px;margin:12px auto}.editor-content :deep(blockquote){margin:10px 0;padding-left:14px;border-left:3px solid var(--amber);color:var(--muted)}
</style>
