<script setup lang="ts">
import { useAuth } from './composables/useAuth';
const { isAuthenticated } = useAuth();
</script>

<template>
  <nav v-if="isAuthenticated">
    <router-link to="/dashboard">Dashboard</router-link>
    <router-link to="/locations">Locations</router-link>
  </nav>
  <router-view />
</template>
