<script setup lang="ts">
defineProps<{
  slug: string;
}>();
</script>

<template>
  <div class="archive">
    <router-link to="/locations">← Locations</router-link>
    <h1>Version history</h1>
    <p>Location: /{{ slug }}</p>
  </div>
</template>
