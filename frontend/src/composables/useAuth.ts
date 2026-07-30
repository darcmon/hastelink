import { ref, computed } from 'vue';

// Module-level = shared across every component that imports this
const token = ref<string | null>(localStorage.getItem('token'));

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value);

  function setToken(newToken: string) {
    token.value = newToken;
    localStorage.setItem('token', newToken);
  }

  function logout() {
    token.value = null;
    localStorage.removeItem('token');
  }

  return { token, isAuthenticated, setToken, logout };
}
