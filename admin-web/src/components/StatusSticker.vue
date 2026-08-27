<script setup lang="ts">
const props = defineProps<{ status: string }>()
const labels: Record<string, string> = { active: '正常', published: '已发布', hidden: '已隐藏', closed: '已关闭', disabled: '已禁用' }
</script>
<template><span class="status-sticker" :class="`is-${props.status}`">{{ labels[props.status] || props.status }}</span></template>
