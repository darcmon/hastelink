<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';

const router = useRouter();
const { logout } = useAuth();

function handleLogout() {
  logout();
  router.push('/login');
}
</script>

<template>
  <div>
    <h1>Dashboard</h1>
    <p>You're in. Pending approvals will live here.</p>
    <button @click="handleLogout">Log out</button>
  </div>
</template>
