<script setup lang="ts">
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const error = new URLSearchParams(window.location.search).get('error');
</script>

<template>
  <div class="login-page">
    <h1>Hastelink</h1>

    <p v-if="error === 'unauthorized'" class="error">
      Your account isn't authorized. Contact your administrator.
    </p>
    <p v-else-if="error === 'provider'" class="error">
      Sign-in failed. Please try again.
    </p>

    <a :href="`${API_URL}/admin/auth/microsoft`" class="sso-btn">
      Sign in with Microsoft
    </a>
    <a :href="`${API_URL}/admin/auth/google`" class="sso-btn">
      Sign in with Google
    </a>
  </div>
</template>
