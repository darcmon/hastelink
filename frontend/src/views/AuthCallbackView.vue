<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';

const router = useRouter();
const { setToken } = useAuth();

onMounted(() => {
  const token = new URLSearchParams(window.location.search).get('token');
  if (token) {
    setToken(token);
    router.replace('/dashboard'); // replace: no history entry with the token in it
  } else {
    router.replace('/login');
  }
});
</script>

<template>
  <p>Signing you in…</p>
</template>
