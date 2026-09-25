export default function Spinner({ texto = 'Cargando…' }) {
  return (
    <div className="spinner-contenedor" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}
