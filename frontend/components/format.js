// Formato de fechas para mostrar en pantalla (es-PE)

// "2026-09-26" → Date local sin desfase de zona horaria
export function parseFecha(iso) {
  const [anio, mes, dia] = iso.split('-').map(Number);
  return new Date(anio, mes - 1, dia);
}

export function formatFechaLarga(iso) {
  return parseFecha(iso).toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function formatFechaCorta(iso) {
  return parseFecha(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short' });
}

export function formatFechaHora(isoDateTime) {
  return new Date(isoDateTime).toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
}

// Fecha de hoy como "YYYY-MM-DD" (hora local)
export function hoyIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function sumarDias(iso, dias) {
  const d = parseFecha(iso);
  d.setDate(d.getDate() + dias);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
