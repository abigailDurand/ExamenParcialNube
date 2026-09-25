import { request } from './api.js';

// --- Públicos ---
export function getPredicciones(dias) {
  const query = dias ? `?dias=${dias}` : '';
  return request(`/predicciones${query}`, { auth: false });
}

// --- Solo administrador ---
export function registrarVisita(fecha, cantidadVisitantes) {
  return request('/visitas', {
    method: 'POST',
    body: { fecha, cantidad_visitantes: cantidadVisitantes },
  });
}

export function getVisitas(desde, hasta) {
  return request(`/visitas?desde=${desde}&hasta=${hasta}`);
}

export function getFeriados(anio) {
  return request(`/feriados?anio=${anio}`);
}

export function agregarFeriado(fecha, nombre) {
  return request('/feriados', { method: 'POST', body: { fecha, nombre } });
}

export function quitarFeriado(fecha) {
  return request(`/feriados/${fecha}`, { method: 'DELETE' });
}

export function getMetricas() {
  return request('/modelo/metricas');
}

export function reentrenarModelo() {
  return request('/modelo/reentrenar', { method: 'POST' });
}
