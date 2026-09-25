// El token JWT se guarda en sessionStorage (ver specs/login-specs.md)
const KEY = 'laspavas_token';

export function getToken() {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function saveToken(token) {
  try {
    sessionStorage.setItem(KEY, token);
  } catch {
    // sin almacenamiento disponible: la sesión dura lo que dure la pestaña
  }
}

export function clearToken() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // nada que borrar
  }
}
