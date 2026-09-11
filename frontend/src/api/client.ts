const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
    return;
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({
      detail: 'Request failed',
    }));
    let message = response.statusText || 'Request failed';

    if (typeof err.detail === 'string') {
      message = err.detail;
    } else if (Array.isArray(err.detail)) {
      const messages = err.detail
        .map((item: unknown) => {
          if (
            typeof item === 'object' &&
            item !== null &&
            'msg' in item &&
            typeof item.msg === 'string'
          ) {
            return item.msg;
          }
          return '';
        })
        .filter((message: string) => message.length > 0);

      if (messages.length > 0) {
        message = messages.join('; ');
      }
    }

    throw new Error(message);
  }

  // 204 No content has no body to parse
  if (response.status === 204) return null;
  return response.json();
}

export default {
  get: (path: string) => request(path),
  post: (path: string, body?: unknown) =>
    request(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),
  postForm: async (path: string, formData: FormData) => {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    // Deliberately NO Content-Type — the browser sets multipart boundary itself

    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
      return;
    }
    if (!response.ok) {
      const err = await response
        .json()
        .catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || response.statusText);
    }
    return response.json();
  },
  patch: (path: string, body: unknown) =>
    request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path: string) => request(path, { method: 'DELETE' }),
};
