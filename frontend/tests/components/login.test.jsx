// test-specs.md › FRONTEND › Pruebas de componentes — Vista de login y rutas protegidas
import '@testing-library/jest-dom/vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderApp, simularFetch } from '../helpers.jsx';

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

async function completarLogin(email, password) {
  const user = userEvent.setup();
  if (email) await user.type(screen.getByLabelText('Correo'), email);
  if (password) await user.type(screen.getByLabelText('Contraseña'), password);
  await user.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
}

describe('Vista de login', () => {
  it.each([
    ['campos vacíos', '', ''],
    ['sin contraseña', 'admin@correo.com', ''],
    ['correo mal formado', 'admin-correo.com', 'clave'],
  ])('Spec: %s → muestra error y no llama a la API', async (_caso, email, password) => {
    const fetchMock = simularFetch({});
    renderApp('/login');
    await completarLogin(email, password);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('Spec: credenciales inválidas → muestra el mensaje de error del backend', async () => {
    simularFetch({ 'POST /auth/login': [401, { detail: 'Correo o contraseña incorrectos' }] });
    renderApp('/login');
    await completarLogin('admin@correo.com', 'mala');
    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos');
    expect(sessionStorage.length).toBe(0);
  });

  it('Spec: login correcto → guarda el token y redirige al panel del administrador', async () => {
    simularFetch({
      'POST /auth/login': [200, { access_token: 'token-de-prueba', token_type: 'bearer', expires_in: 3600 }],
      'GET /locations': [200, []],
      'GET /consultations/recent': [200, []],
    });
    renderApp('/login');
    await completarLogin('admin@correo.com', 'clave');
    expect(await screen.findByRole('heading', { name: 'Panel del administrador' })).toBeInTheDocument();
    expect(Object.values({ ...sessionStorage })).toContain('token-de-prueba');
  });

  it('UI: el botón se deshabilita mientras la petición está en curso', async () => {
    simularFetch({ 'POST /auth/login': () => new Promise(() => {}) });
    renderApp('/login');
    await completarLogin('admin@correo.com', 'clave');
    expect(screen.getByRole('button', { name: /Ingresando/ })).toBeDisabled();
  });
});

describe('Rutas protegidas', () => {
  it('Spec: sin token guardado → redirige a la vista de login', async () => {
    simularFetch({});
    renderApp('/admin');
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
  });

  it('Spec: panel solo accesible con token; "Cerrar sesión" borra el token y vuelve a la vista pública', async () => {
    sessionStorage.setItem('laspavas_token', 'token-de-prueba');
    simularFetch({
      'GET /locations': [200, []],
      'GET /consultations/recent': [200, []],
      'GET /predicciones': [200, []],
    });
    renderApp('/admin');
    await userEvent.click(await screen.findByRole('button', { name: 'Cerrar sesión' }));
    expect(await screen.findByRole('heading', { name: 'Visitantes a Las Pavas' })).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem('laspavas_token')).toBeNull());
  });
});
