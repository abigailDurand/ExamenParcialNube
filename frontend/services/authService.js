import { request } from './api.js';
import { clearToken, getToken, saveToken } from './tokenStorage.js';

export async function login(email, password) {
  // auth: false → un 401 aquí es "credenciales incorrectas", no "sesión vencida"
  const data = await request('/auth/login', { method: 'POST', body: { email, password }, auth: false });
  saveToken(data.access_token);
  return data;
}

export function logout() {
  clearToken();
}

export function isAuthenticated() {
  return Boolean(getToken());
}
