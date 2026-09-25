// test-specs.md › FRONTEND › Pruebas de servicios (/services)
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

function fetchQueResponde(status, body) {
  return vi.fn(() =>
    Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) }),
  );
}

beforeEach(() => {
  sessionStorage.clear();
  vi.resetModules(); // BASE_URL se calcula al importar api.js
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('services', () => {
  it('Spec: las llamadas usan VITE_BACKEND_URL del .env (no URL hardcodeada)', async () => {
    vi.stubEnv('VITE_BACKEND_URL', 'http://backend-de-prueba.test:1234/');
    const fetchMock = fetchQueResponde(200, []);
    vi.stubGlobal('fetch', fetchMock);
    const { getPredicciones } = await import('../../services/prediccionService.js');
    await getPredicciones(3);
    expect(fetchMock.mock.calls[0][0]).toBe('http://backend-de-prueba.test:1234/api/v1/predicciones?dias=3');
  });

  it('Spec: se envía el header Authorization: Bearer <token> en cada llamada protegida', async () => {
    sessionStorage.setItem('laspavas_token', 'token-de-prueba');
    const fetchMock = fetchQueResponde(200, []);
    vi.stubGlobal('fetch', fetchMock);
    const weather = await import('../../services/weatherService.js');
    const prediccion = await import('../../services/prediccionService.js');
    await weather.getLocations();
    await weather.getWeather('Tingo María');
    await weather.getRecentConsultations();
    await prediccion.getVisitas('2026-09-01', '2026-09-30');
    await prediccion.getFeriados(2026);
    await prediccion.getMetricas();
    for (const [, opciones] of fetchMock.mock.calls) {
      expect(opciones.headers.Authorization).toBe('Bearer token-de-prueba');
    }
  });

  it('Spec: maneja respuestas de error del backend sin romper la UI (ApiError con status y detalle)', async () => {
    vi.stubGlobal('fetch', fetchQueResponde(503, { detail: 'No se pudo obtener el clima de esta ubicación' }));
    const { getWeather } = await import('../../services/weatherService.js');
    const { ApiError } = await import('../../services/api.js');
    const error = await getWeather('Tingo María').catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(503);
    expect(error.message).toBe('No se pudo obtener el clima de esta ubicación');
  });

  it('Spec: error de red → ApiError (status 0), no una excepción sin controlar', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))));
    const { getLocations } = await import('../../services/weatherService.js');
    const error = await getLocations().catch((e) => e);
    expect(error.status).toBe(0);
  });

  it('login: guarda el token en sessionStorage; un 401 del login no dispara la redirección', async () => {
    const { setUnauthorizedHandler } = await import('../../services/api.js');
    const redirigir = vi.fn();
    setUnauthorizedHandler(redirigir);
    vi.stubGlobal('fetch', fetchQueResponde(401, { detail: 'Correo o contraseña incorrectos' }));
    const auth = await import('../../services/authService.js');
    await expect(auth.login('admin@correo.com', 'mala')).rejects.toMatchObject({ status: 401 });
    expect(redirigir).not.toHaveBeenCalled();

    vi.stubGlobal('fetch', fetchQueResponde(200, { access_token: 'nuevo-token', token_type: 'bearer', expires_in: 3600 }));
    await auth.login('admin@correo.com', 'buena');
    expect(sessionStorage.getItem('laspavas_token')).toBe('nuevo-token');
    expect(auth.isAuthenticated()).toBe(true);
  });

  it('401 en endpoint protegido: borra el token y llama a la redirección al login', async () => {
    sessionStorage.setItem('laspavas_token', 'vencido');
    const { setUnauthorizedHandler } = await import('../../services/api.js');
    const redirigir = vi.fn();
    setUnauthorizedHandler(redirigir);
    vi.stubGlobal('fetch', fetchQueResponde(401, { detail: 'No autorizado' }));
    const { getMetricas } = await import('../../services/prediccionService.js');
    await expect(getMetricas()).rejects.toMatchObject({ status: 401 });
    expect(redirigir).toHaveBeenCalledOnce();
    expect(sessionStorage.getItem('laspavas_token')).toBeNull();
  });
});
