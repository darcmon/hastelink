<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '../composables/useAuth';
import api from '../api/client';

interface PendingVersion {
  id: string;
  location_slug: string;
  location_display_name: string;
  kind: 'file' | 'link';
  link_url: string | null;
  link_mode: 'redirect' | null;
  original_filename: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  version_number: number;
  uploaded_by: string;
  uploaded_at: string;
}

const router = useRouter();
const { logout } = useAuth();

const pending = ref<PendingVersion[]>([]);
const loading = ref(true);
const error = ref('');
const actioningId = ref<string | null>(null);

async function loadPending() {
  loading.value = true;
  error.value = '';
  try {
    pending.value = await api.get('/admin/versions/pending');
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load';
  } finally {
    loading.value = false;
  }
}

async function approve(id: string) {
  actioningId.value = id;
  try {
    await api.post(`/admin/versions/${id}/approve`);
    await loadPending();
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Approve failed';
  } finally {
    actioningId.value = null;
  }
}

async function reject(id: string) {
  if (!confirm('Reject this version?')) return;
  actioningId.value = id;
  try {
    await api.post(`/admin/versions/${id}/reject`);
    await loadPending();
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Reject failed';
  } finally {
    actioningId.value = null;
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function handleLogout() {
  logout();
  router.push('/login');
}

onMounted(loadPending);
</script>

<template>
  <div class="dashboard">
    <header>
      <h1>Pending Approvals</h1>
      <button @click="handleLogout">Log out</button>
    </header>

    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="pending.length === 0">
      No pending versions. Everything's up to date.
    </p>

    <ul v-else class="pending-list">
      <li v-for="v in pending" :key="v.id" class="pending-item">
        <div class="info">
          <strong>
            {{ v.kind === 'link' ? v.link_url : v.original_filename }}
          </strong>

          <span class="meta">
            <template v-if="v.kind === 'link'"> Redirect link · </template>
            <template v-else-if="v.file_size_bytes !== null">
              {{ formatSize(v.file_size_bytes) }} ·
            </template>
            v{{ v.version_number }} · {{ v.location_display_name }} (/{{
              v.location_slug
            }})
          </span>

          <span class="meta">Submitted by {{ v.uploaded_by }}</span>
        </div>
        <div class="actions">
          <button :disabled="actioningId === v.id" @click="approve(v.id)">
            Approve
          </button>
          <button :disabled="actioningId === v.id" @click="reject(v.id)">
            Reject
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>
