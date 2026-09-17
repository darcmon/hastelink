<script setup lang="ts">
import { ref, watch } from 'vue';
import type { ArchivedVersion, ArchiveResponse } from '../types/version';
import api from '../api/client';

const props = defineProps<{
  slug: string;
}>();

const archive = ref<ArchiveResponse | null>(null);
const downloadingId = ref<string | null>(null);
const downloadError = ref('');
const loading = ref(false);
const error = ref('');
const statusFilter = ref('');
const page = ref(1);
const perPage = 20;

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

async function downloadVersion(version: ArchivedVersion) {
  if (version.kind !== 'file' || downloadingId.value !== null) return;

  downloadingId.value = version.id;
  downloadError.value = '';

  try {
    const blob = await api.download(
      `/admin/versions/${encodeURIComponent(version.id)}/download`,
    );
    if (!blob) return;

    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');

    try {
      anchor.href = objectUrl;
      anchor.download = version.original_filename || 'download';
      document.body.appendChild(anchor);
      anchor.click();
    } finally {
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    }
  } catch (e) {
    downloadError.value = e instanceof Error ? e.message : 'Download failed';
  } finally {
    downloadingId.value = null;
  }
}

watch([() => props.slug, statusFilter], () => {
  page.value = 1;
});

watch(
  [() => props.slug, page, statusFilter],
  async ([slug, currentPage, status], _previousValues, onCleanup) => {
    let active = true;
    onCleanup(() => {
      active = false;
    });

    loading.value = true;
    error.value = '';
    archive.value = null;

    try {
      const statusQuery = status ? `&status=${encodeURIComponent(status)}` : '';

      const data = await api.get(
        `/admin/locations/${encodeURIComponent(slug)}/versions?page=${currentPage}&per_page=${perPage}${statusQuery}`,
      );
      if (active && data) {
        archive.value = data;
      }
    } catch (e) {
      if (active) {
        error.value = e instanceof Error ? e.message : 'Failed to load history';
      }
    } finally {
      if (active) {
        loading.value = false;
      }
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="archive">
    <router-link to="/locations">← Locations</router-link>
    <h1>Version history</h1>
    <p>Location: /{{ slug }}</p>

    <div class="field">
      <label for="status-filter">Status</label>
      <select id="status-filter" v-model="statusFilter">
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="superseded">Superseded</option>
      </select>
    </div>

    <p v-if="downloadError" class="error" role="alert">
      {{ downloadError }}
    </p>

    <p v-if="loading">Loading history…</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <template v-else-if="archive">
      <h2>{{ archive.location_display_name }}</h2>
      <p v-if="archive.total === 0">
        {{
          statusFilter ? 'No versions match this status.' : 'No versions yet.'
        }}
      </p>

      <template v-else>
        <p>
          Page {{ page }} · {{ archive.total }}
          {{ statusFilter ? 'matching versions' : 'versions total' }}
        </p>

        <ul>
          <li v-for="version in archive.versions" :key="version.id">
            <strong>
              {{
                version.kind === 'link'
                  ? version.link_url
                  : version.original_filename
              }}
            </strong>
            <p>
              v{{ version.version_number }} · {{ version.status }} ·
              {{ version.kind === 'link' ? 'Redirect link' : 'File' }}
            </p>
            <p>Submitted by {{ version.uploaded_by }}</p>
            <p>Submitted on {{ formatDate(version.uploaded_at) }}</p>
            <button
              v-if="version.kind === 'file'"
              type="button"
              :disabled="downloadingId !== null"
              @click="downloadVersion(version)"
            >
              {{
                downloadingId === version.id ? 'Downloading…' : 'Download file'
              }}
            </button>
          </li>
        </ul>
      </template>
    </template>

    <nav aria-label="Version history pages">
      <button type="button" :disabled="loading || page === 1" @click="page--">
        Previous
      </button>
      <button
        type="button"
        :disabled="loading || !archive || page * perPage >= archive.total"
        @click="page++"
      >
        Next
      </button>
    </nav>
  </div>
</template>
