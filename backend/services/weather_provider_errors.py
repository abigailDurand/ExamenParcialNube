"""Excepciones compartidas por los clientes de clima (ver condicional-api-specs.md)."""


class WeatherLocationNotFoundError(Exception):
    """El proveedor no encontró la ubicación."""


class WeatherProviderError(Exception):
    """Cualquier otro fallo del proveedor: red, timeout, status inesperado."""
