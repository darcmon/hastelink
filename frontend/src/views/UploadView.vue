<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '../api/client';

interface Location {
  slug: string;
  display_name: string;
}

const ALLOWED = ['application/pdf', 'image/png', 'image/jpeg'];
const MAX_MB = 50;

const locations = ref<Location[]>([]);
const selectedSlug = ref('');
const selectedFile = ref<File | null>(null);
const dragging = ref(false);
const error = ref('');
const result = ref<{
  label: string;
  version_number: number;
} | null>(null);
const uploading = ref(false);
const submissionKind = ref<'file' | 'link'>('file');
const linkUrl = ref('');

async function loadLocations() {
  const data = await api.get('/admin/locations');
  locations.value = data.locations;
}

function validate(file: File): boolean {
  if (!ALLOWED.includes(file.type)) {
    error.value = 'File type not allowed. Use PDF, PNG, or JPEG.';
    return false;
  }
  if (file.size > MAX_MB * 1024 * 1024) {
    error.value = `File too large. Max ${MAX_MB}MB.`;
    return false;
  }
  if (file.size === 0) {
    error.value = 'File is empty.';
    return false;
  }
  error.value = '';
  return true;
}

function onDrop(e: DragEvent) {
  dragging.value = false;
  const file = e.dataTransfer?.files[0];
  if (file && validate(file)) selectedFile.value = file;
}

function onFileInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file && validate(file)) selectedFile.value = file;
}

async function upload() {
  if (!selectedFile.value || !selectedSlug.value) return;
  uploading.value = true;
  error.value = '';
  result.value = null;
  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    const created = await api.postForm(
      `/admin/locations/${selectedSlug.value}/upload`,
      formData,
    );
    if (!created) return;

    result.value = {
      label: created.original_filename,
      version_number: created.version_number,
    };
    selectedFile.value = null;
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Upload failed';
  } finally {
    uploading.value = false;
  }
}

async function submitLink() {
  const url = linkUrl.value.trim();
  if (!url || !selectedSlug.value || uploading.value) return;

  uploading.value = true;
  error.value = '';
  result.value = null;

  try {
    const created = await api.post(
      `/admin/locations/${selectedSlug.value}/link`,
      {
        link_url: url,
        link_mode: 'redirect',
      },
    );
    if (!created) return;

    result.value = {
      label: created.link_url,
      version_number: created.version_number,
    };
    linkUrl.value = '';
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Link submission failed';
  } finally {
    uploading.value = false;
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

onMounted(loadLocations);
</script>

<template>
  <div class="upload">
    <h1>Submit a Version</h1>

    <div class="field">
      <label>Location</label>
      <select v-model="selectedSlug" :disabled="uploading">
        <option value="" disabled>Select a location…</option>
        <option v-for="loc in locations" :key="loc.slug" :value="loc.slug">
          {{ loc.display_name }} (/{{ loc.slug }})
        </option>
      </select>
    </div>

    <div class="field">
      <label for="submission-kind">Version type</label>
      <select
        id="submission-kind"
        v-model="submissionKind"
        :disabled="uploading"
      >
        <option value="file">File</option>
        <option value="link">Redirect link</option>
      </select>
    </div>

    <div v-if="selectedSlug && submissionKind === 'link'" class="field">
      <label for="link-url">Destination URL</label>
      <input
        id="link-url"
        v-model="linkUrl"
        type="url"
        placeholder="https://example.com/handbook"
        :disabled="uploading"
      />
      <small>The link will be checked and submitted for approval.</small>
      <button
        type="button"
        :disabled="uploading || !linkUrl.trim()"
        @click="submitLink"
      >
        {{ uploading ? 'Checking link…' : 'Submit link' }}
      </button>
    </div>

    <div
      v-if="submissionKind === 'file' && selectedSlug && !selectedFile"
      class="dropzone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
      @click="($refs.fileInput as HTMLInputElement).click()"
    >
      <p>Drop a file here or click to browse</p>
      <small>PDF, PNG, JPEG · Max {{ MAX_MB }}MB</small>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf,image/png,image/jpeg"
        style="display: none"
        @change="onFileInput"
      />
    </div>

    <div v-if="submissionKind === 'file' && selectedFile" class="preview">
      <span>{{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})</span>
      <button :disabled="uploading" @click="upload">
        {{ uploading ? 'Uploading…' : 'Upload' }}
      </button>
      <button @click="selectedFile = null">Remove</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="success">
      Submitted {{ result.label }} as v{{ result.version_number }} — pending
      approval. Review it on the Dashboard.
    </div>
  </div>
</template>
