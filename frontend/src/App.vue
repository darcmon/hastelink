<script setup lang="ts">
import ThemeSelector from './components/ThemeSelector.vue';
import { useAuth } from './composables/useAuth';
const { isAuthenticated } = useAuth();
</script>

<template>
  <ThemeSelector />

  <nav v-if="isAuthenticated">
    <router-link to="/dashboard">Dashboard</router-link>
    <router-link to="/locations">Locations</router-link>
    <router-link to="/upload">Upload</router-link>
  </nav>

  <router-view />
</template>
