<script setup lang="ts">
import { computed } from 'vue';
import { useTheme } from '../composables/useTheme';
import type { ThemePreference } from '../composables/useTheme';

const { preference, setTheme } = useTheme();

const selectedTheme = computed<ThemePreference>({
  get: () => preference.value,
  set: (value) => setTheme(value),
});
</script>

<template>
  <label class="theme-selector">
    <span>Theme</span>

    <select v-model="selectedTheme">
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  </label>
</template>

<style scoped>
.theme-selector {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text);
}

select {
  min-height: 44px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-small);
  color: var(--color-text);
  background-color: var(--color-surface);
}
</style>
