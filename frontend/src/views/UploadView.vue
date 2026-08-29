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
  original_filename: string;
  version_number: number;
} | null>(null);
const uploading = ref(false);

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
    result.value = await api.postForm(
      `/admin/locations/${selectedSlug.value}/upload`,
      formData,
    );
    selectedFile.value = null;
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Upload failed';
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
    <h1>Upload File</h1>

    <div class="field">
      <label>Location</label>
      <select v-model="selectedSlug">
        <option value="" disabled>Select a location…</option>
        <option v-for="loc in locations" :key="loc.slug" :value="loc.slug">
          {{ loc.display_name }} (/{{ loc.slug }})
        </option>
      </select>
    </div>

    <div
      v-if="selectedSlug && !selectedFile"
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

    <div v-if="selectedFile" class="preview">
      <span>{{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})</span>
      <button :disabled="uploading" @click="upload">
        {{ uploading ? 'Uploading…' : 'Upload' }}
      </button>
      <button @click="selectedFile = null">Remove</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="success">
      Uploaded {{ result.original_filename }} as v{{ result.version_number }} —
      pending approval. Review it on the Dashboard.
    </div>
  </div>
</template>
