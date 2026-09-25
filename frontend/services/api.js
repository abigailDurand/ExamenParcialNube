// Cliente HTTP común. La URL del backend se lee de VITE_BACKEND_URL (.env).
import { clearToken, getToken } from './tokenStorage.js';

const BASE_URL = `${(import.meta.env.VITE_BACKEND_URL ?? '').replace(/\/$/, '')}/api/v1`;

let onUnauthorized = () => {};

// La app registra aquí qué hacer ante un 401 (volver al login)
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `Error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor');
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && auth) {
      clearToken();
      onUnauthorized();
    }
    throw new ApiError(response.status, data?.detail);
  }
  return data;
}
