<script setup lang="ts">
import { ref, watch } from 'vue'
import { STORE_IMAGE_FALLBACK } from '../utils/store'

const props = withDefaults(defineProps<{ src?: string | null; fallback?: string; mode?: string }>(), {
  fallback: STORE_IMAGE_FALLBACK,
  mode: 'aspectFill',
})
const currentSource = ref(props.src || props.fallback)

watch(() => props.src, (value) => {
  currentSource.value = value || props.fallback
})

function handleError() {
  currentSource.value = props.fallback
}
</script>

<template>
  <image :src="currentSource" :mode="mode" @error="handleError" />
</template>
