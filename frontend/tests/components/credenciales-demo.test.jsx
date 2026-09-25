// test-specs.md › FRONTEND › Credenciales de demostración (solo si las variables tienen valor)
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => vi.resetModules()); // las variables se leen al importar el componente
afterEach(() => vi.unstubAllEnvs());

async function renderCredenciales() {
  const { default: CredencialesDemo } = await import('../../components/CredencialesDemo.jsx');
  return render(<CredencialesDemo />);
}

describe('Credenciales de demostración', () => {
  it('Spec: se muestran si VITE_DEMO_ADMIN_EMAIL y VITE_DEMO_ADMIN_PASSWORD tienen valor', async () => {
    vi.stubEnv('VITE_DEMO_ADMIN_EMAIL', 'profe@correo.com');
    vi.stubEnv('VITE_DEMO_ADMIN_PASSWORD', 'clave-demo');
    await renderCredenciales();
    expect(screen.getByText('profe@correo.com')).toBeInTheDocument();
    expect(screen.getByText('clave-demo')).toBeInTheDocument();
  });

  it.each([
    ['ambas vacías', '', ''],
    ['falta la contraseña', 'profe@correo.com', ''],
    ['falta el correo', '', 'clave-demo'],
  ])('Spec: no se muestra nada si %s', async (_caso, email, password) => {
    vi.stubEnv('VITE_DEMO_ADMIN_EMAIL', email);
    vi.stubEnv('VITE_DEMO_ADMIN_PASSWORD', password);
    const { container } = await renderCredenciales();
    expect(container).toBeEmptyDOMElement();
  });
});
