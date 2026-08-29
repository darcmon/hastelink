<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '../api/client';

interface Location {
  id: string;
  slug: string;
  display_name: string;
  description: string | null;
  reminder_email: string | null;
  current_approved_version_id: string | null;
}

const locations = ref<Location[]>([]);
const loading = ref(true);
const error = ref('');

const showForm = ref(false);
const form = ref({
  slug: '',
  display_name: '',
  description: '',
  reminder_email: '',
});
const formError = ref('');
const submitting = ref(false);

async function loadLocations() {
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/admin/locations');
    locations.value = data.locations;
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load';
  } finally {
    loading.value = false;
  }
}

async function createLocation() {
  formError.value = '';
  submitting.value = true;
  try {
    await api.post('/admin/locations', {
      slug: form.value.slug,
      display_name: form.value.display_name,
      description: form.value.description || null,
      reminder_email: form.value.reminder_email || null,
    });

    form.value = {
      slug: '',
      display_name: '',
      description: '',
      reminder_email: '',
    };
    showForm.value = false;
    await loadLocations();
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'Failed to create';
  } finally {
    submitting.value = false;
  }
}

onMounted(loadLocations);
</script>

<template>
  <div class="locations">
    <header>
      <h1>Locations</h1>
      <button @click="showForm = !showForm">
        {{ showForm ? 'Cancel' : '+ New Location' }}
      </button>
    </header>

    <!-- Create form -->
    <div v-if="showForm" class="create-form">
      <div class="field">
        <label>Slug (URL path)</label>
        <input v-model="form.slug" placeholder="documents" />
        <small>Becomes /{{ form.slug || '...' }}</small>
      </div>
      <div class="field">
        <label>Display Name</label>
        <input v-model="form.display_name" placeholder="Documents" />
      </div>
      <div class="field">
        <label>Description (optional)</label>
        <input v-model="form.description" />
      </div>
      <div class="field">
        <label>Reminder Email (optional)</label>
        <input v-model="form.reminder_email" placeholder="email" />
      </div>
      <p v-if="formError">{{ formError }}</p>
      <button :disabled="submitting" @click="createLocation">
        {{ submitting ? 'Creating...' : 'Create' }}
      </button>
    </div>

    <!-- List -->
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="locations.length === 0">
      No locations yet. Create one to get started.
    </p>

    <ul v-else class="location-list">
      <li v-for="loc in locations" :key="loc.id" class="location-item">
        <div>
          <strong>{{ loc.display_name }}</strong>
          <span class="slug">/{{ loc.slug }}</span>
          <p v-if="loc.description" class="desc">{{ loc.description }}</p>
        </div>
        <div class="status">
          <span :class="loc.current_approved_version_id ? 'serving' : 'empty'">
            {{
              loc.current_approved_version_id ? 'Serving file' : 'No file yet'
            }}
          </span>
          <router-link :to="`locations/${loc.slug}/archive`"
            >Archive →</router-link
          >
        </div>
      </li>
    </ul>
  </div>
</template>
