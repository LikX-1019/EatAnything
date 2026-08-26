<script setup lang="ts">
defineProps<{ title: string; note?: string }>()
</script>
<template><div class="page-heading"><span class="heading-tape" /><div><h1>{{ title }}</h1><p>{{ note }}</p></div><span class="heading-doodle">✿</span></div></template>
