// Utilidades comunes: fetch simulado (nunca se llama al backend real) y render con router.
import { configure, render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { vi } from 'vitest';
import App from '../components/App.jsx';

// El panel se carga de forma diferida (lazy): la primera vez Vitest compila Recharts en frío
configure({ asyncUtilTimeout: 5000 });

export function respuesta(status, body) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => (body === undefined ? Promise.reject(new Error('sin cuerpo')) : Promise.resolve(body)),
  });
}

/**
 * rutas: { 'GET /locations': [200, [...]] | (url, opciones) => Promise }
 * Devuelve el mock de fetch para inspeccionar las llamadas.
 */
export function simularFetch(rutas) {
  const fetchMock = vi.fn((url, opciones = {}) => {
    const metodo = opciones.method ?? 'GET';
    const ruta = new URL(url, 'http://localhost').pathname.replace(/^\/api\/v1/, '');
    const clave = `${metodo} ${ruta}`;
    const manejador = rutas[clave];
    if (!manejador) return respuesta(404, { detail: `sin simular: ${clave}` });
    return typeof manejador === 'function' ? manejador(url, opciones) : respuesta(...manejador);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

export function renderApp(rutaInicial = '/') {
  return render(
    <MemoryRouter initialEntries={[rutaInicial]}>
      <App />
    </MemoryRouter>,
  );
}

export const PREDICCIONES = [
  { fecha: '2026-09-25', visitantes_predichos: 25, nivel_afluencia: 'Baja', lluvia_mm: 18.2, temp_max: 27.4,
    version_modelo: 1, entrenado_con_sinteticos: true, dato_incompleto: false },
  { fecha: '2026-09-26', visitantes_predichos: 45, nivel_afluencia: 'Media', lluvia_mm: 0.3, temp_max: 31.6,
    version_modelo: 1, entrenado_con_sinteticos: true, dato_incompleto: false },
  { fecha: '2026-09-27', visitantes_predichos: 74, nivel_afluencia: 'Alta', lluvia_mm: 0, temp_max: 32.5,
    version_modelo: 1, entrenado_con_sinteticos: true, dato_incompleto: true },
];
