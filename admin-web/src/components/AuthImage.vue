<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { authenticatedImage } from '../api/client'
const props = defineProps<{ src: string; alt?: string }>()
const objectUrl = ref('')
async function load() { if (objectUrl.value) URL.revokeObjectURL(objectUrl.value); objectUrl.value = await authenticatedImage(props.src).catch(() => '') }
watch(() => props.src, load, { immediate: true })
onBeforeUnmount(() => { if (objectUrl.value) URL.revokeObjectURL(objectUrl.value) })
</script>
<template><div class="polaroid"><img v-if="objectUrl" :src="objectUrl" :alt="alt || '打卡照片'" /><div v-else class="image-fallback">照片暂不可见</div></div></template>
