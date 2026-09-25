// Credenciales de demostración para la revisión (ver specs/ui-design-specs.md).
// Se leen de frontend/.env; si no están definidas, no se muestra nada.
const EMAIL = import.meta.env.VITE_DEMO_ADMIN_EMAIL;
const PASSWORD = import.meta.env.VITE_DEMO_ADMIN_PASSWORD;

export default function CredencialesDemo() {
  if (!EMAIL || !PASSWORD) return null;
  return (
    <aside className="credenciales-demo" aria-label="Credenciales de demostración">
      <strong>Acceso de demostración (administrador)</strong>
      <span>
        Correo: <code>{EMAIL}</code>
      </span>
      <span>
        Contraseña: <code>{PASSWORD}</code>
      </span>
    </aside>
  );
}
