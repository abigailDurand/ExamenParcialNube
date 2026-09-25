// test-specs.md › FRONTEND › Pruebas de componentes — Consulta Meteorológica (estados cargando, éxito, error, 401)
import '@testing-library/jest-dom/vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderApp, simularFetch } from '../helpers.jsx';

const UBICACIONES = [{ id: 1, name: 'Tingo María', type: 'region' }];
const CLIMA = { location: 'Tingo María', temperature: '24°C', condition: 'Despejado', humidity: '60%', source: 'weatherapi' };

beforeEach(() => {
  sessionStorage.clear();
  sessionStorage.setItem('laspavas_token', 'token-de-prueba');
});
afterEach(() => vi.unstubAllGlobals());

function rutas(weather) {
  return {
    'GET /locations': [200, UBICACIONES],
    'GET /consultations/recent': [200, []],
    'GET /weather': weather,
  };
}

async function seleccionarYConsultar() {
  const user = userEvent.setup();
  const select = await screen.findByLabelText('Región');
  await within(select).findByRole('option', { name: 'Tingo María' });
  await user.selectOptions(select, 'Tingo María');
  await user.click(screen.getByRole('button', { name: 'Consultar' }));
}

describe('Consulta Meteorológica', () => {
  it('Spec: el menú desplegable se llena con los datos de GET /api/v1/locations', async () => {
    simularFetch(rutas([200, CLIMA]));
    renderApp('/admin');
    const select = await screen.findByLabelText('Región');
    expect(await within(select).findByRole('option', { name: 'Tingo María' })).toBeInTheDocument();
    expect(within(select).getByRole('option', { name: 'Selecciona una región...' })).toBeInTheDocument();
  });

  it('Spec: el botón "Consultar" está deshabilitado si no hay ubicación seleccionada', async () => {
    simularFetch(rutas([200, CLIMA]));
    renderApp('/admin');
    await screen.findByLabelText('Región');
    expect(screen.getByRole('button', { name: 'Consultar' })).toBeDisabled();
  });

  it('Spec: estado cargando → se muestra el spinner mientras espera la respuesta', async () => {
    simularFetch(rutas(() => new Promise(() => {})));
    renderApp('/admin');
    await seleccionarYConsultar();
    expect(screen.getByRole('status')).toHaveTextContent('Consultando el clima');
    expect(screen.getByRole('button', { name: 'Consultar' })).toBeDisabled();
  });

  it('Spec: estado éxito → la tarjeta muestra Temperatura, Estado y Humedad', async () => {
    simularFetch(rutas([200, CLIMA]));
    renderApp('/admin');
    await seleccionarYConsultar();
    expect(await screen.findByText('24°C')).toBeInTheDocument();
    expect(screen.getByText('Despejado')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('Temperatura')).toBeInTheDocument();
  });

  it.each([[503], [404], [500]])(
    'Spec: estado error (%i) → se muestra "No se pudo obtener el clima de esta ubicación"',
    async (status) => {
      simularFetch(rutas([status, { detail: 'error' }]));
      renderApp('/admin');
      await seleccionarYConsultar();
      expect(await screen.findByText('No se pudo obtener el clima de esta ubicación')).toBeInTheDocument();
    },
  );

  it('Spec: respuesta 401 → se redirige a la pantalla de inicio de sesión', async () => {
    simularFetch(rutas([401, { detail: 'No autorizado' }]));
    renderApp('/admin');
    await seleccionarYConsultar();
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    expect(sessionStorage.getItem('laspavas_token')).toBeNull();
  });

  it('Spec: maneja un error de red sin romper la UI', async () => {
    simularFetch({ ...rutas(() => Promise.reject(new TypeError('Failed to fetch'))) });
    renderApp('/admin');
    await seleccionarYConsultar();
    expect(await screen.findByText('No se pudo obtener el clima de esta ubicación')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Panel del administrador' })).toBeInTheDocument();
  });

  it('UI: clic en una consulta reciente vuelve a consultar esa ubicación', async () => {
    const fetchMock = simularFetch({
      ...rutas([200, CLIMA]),
      'GET /consultations/recent': [200, [{ location: 'Tingo María', created_at: '2026-09-25T10:00:00Z' }]],
    });
    renderApp('/admin');
    await userEvent.click(await screen.findByRole('button', { name: /Tingo María/ }));
    expect(await screen.findByText('24°C')).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/weather?location=Tingo%20Mar%C3%ADa'))).toBe(true);
  });
});

