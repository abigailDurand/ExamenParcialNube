import { request } from './api.js';

export function getLocations() {
  return request('/locations');
}

export function getWeather(location) {
  return request(`/weather?location=${encodeURIComponent(location)}`);
}

export function getRecentConsultations() {
  return request('/consultations/recent');
}
