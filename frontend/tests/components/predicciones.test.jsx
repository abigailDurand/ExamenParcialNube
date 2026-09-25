// test-specs.md › FRONTEND › Pruebas de componentes — Vista pública y gráfico real vs. predicho
import '@testing-library/jest-dom/vitest';
import { cloneElement } from 'react';
import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PREDICCIONES, renderApp, simularFetch } from '../helpers.jsx';

// jsdom no mide tamaños: el contenedor responsivo se reemplaza por uno de tamaño fijo
vi.mock('recharts', async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    ResponsiveContainer: ({ children }) => cloneElement(children, { width: 800, height: 320 }),
  };
});

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe('Vista pública de predicciones', () => {
  it('Spec: muestra las tarjetas de predicción sin sesión, con el color del nivel de afluencia', async () => {
    const fetchMock = simularFetch({ 'GET /predicciones': [200, PREDICCIONES] });
    renderApp('/');
    const tarjetas = await screen.findAllByRole('article');
    expect(tarjetas).toHaveLength(3);
    expect(tarjetas.map((t) => t.className.match(/afluencia-\w+/)[0])).toEqual([
      'afluencia-baja', 'afluencia-media', 'afluencia-alta',
    ]);
    expect(screen.getByText('Afluencia Alta')).toBeInTheDocument();
    const [, opciones] = fetchMock.mock.calls[0];
    expect(opciones.headers.Authorization).toBeUndefined(); // público: sin token
  });

  it('Spec: muestra la nota de dato incompleto', async () => {
    simularFetch({ 'GET /predicciones': [200, PREDICCIONES] });
    renderApp('/');
    expect(await screen.findAllByText('Pronóstico de lluvia no disponible')).toHaveLength(1);
  });

  it('Spec: muestra el mensaje de 503', async () => {
    simularFetch({ 'GET /predicciones': [503, { detail: 'Predicción no disponible por el momento' }] });
    renderApp('/');
    expect(await screen.findByText('Predicción no disponible por el momento')).toBeInTheDocument();
  });

  it('UI: enlace "Ingresar como administrador" lleva al login', async () => {
    simularFetch({ 'GET /predicciones': [200, PREDICCIONES] });
    renderApp('/');
    expect(await screen.findByRole('link', { name: 'Ingresar como administrador' })).toHaveAttribute('href', '/login');
  });
});

describe('Gráfico de visitas reales vs. predichas', () => {
  it('Spec: se dibuja con los datos de la API', async () => {
    sessionStorage.setItem('laspavas_token', 'token-de-prueba');
    simularFetch({
      'GET /visitas': [200, [
        { fecha: '2026-09-20', cantidad_visitantes: 40, es_sintetico: false, visitantes_predichos: 38 },
        { fecha: '2026-09-21', cantidad_visitantes: 72, es_sintetico: false, visitantes_predichos: 70 },
        { fecha: '2026-09-22', cantidad_visitantes: 35, es_sintetico: false, visitantes_predichos: null },
      ]],
    });
    const { container } = renderApp('/admin/grafico');
    expect(await screen.findByText('Reales')).toBeInTheDocument();
    expect(screen.getByText('Predichas')).toBeInTheDocument();
    expect(container.querySelectorAll('.recharts-line')).toHaveLength(2);
  });
});
