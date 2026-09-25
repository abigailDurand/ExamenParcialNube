"""Traducción del estado del clima de cada proveedor al mismo vocabulario en español."""

# WeatherAPI: current.condition.text (en inglés, en minúsculas para comparar)
WEATHERAPI_CONDITION_TRANSLATIONS = {
    "sunny": "Despejado",
    "clear": "Despejado",
    "partly cloudy": "Parcialmente nublado",
    "cloudy": "Nublado",
    "overcast": "Nublado",
    "mist": "Neblina",
    "fog": "Neblina",
    "freezing fog": "Neblina",
    "patchy rain possible": "Lluvia",
    "patchy rain nearby": "Lluvia",
    "patchy light drizzle": "Llovizna",
    "light drizzle": "Llovizna",
    "freezing drizzle": "Llovizna",
    "heavy freezing drizzle": "Llovizna",
    "patchy light rain": "Lluvia",
    "light rain": "Lluvia",
    "moderate rain at times": "Lluvia",
    "moderate rain": "Lluvia",
    "heavy rain at times": "Lluvia",
    "heavy rain": "Lluvia",
    "light freezing rain": "Lluvia",
    "moderate or heavy freezing rain": "Lluvia",
    "light rain shower": "Lluvia",
    "moderate or heavy rain shower": "Lluvia",
    "torrential rain shower": "Lluvia",
    "thundery outbreaks possible": "Tormenta",
    "thundery outbreaks in nearby": "Tormenta",
    "patchy light rain with thunder": "Tormenta",
    "moderate or heavy rain with thunder": "Tormenta",
    "patchy light snow with thunder": "Tormenta",
    "moderate or heavy snow with thunder": "Tormenta",
}

# Palabras clave para textos de WeatherAPI que no estén en el diccionario
_WEATHERAPI_KEYWORDS = [
    ("thunder", "Tormenta"),
    ("snow", "Nieve"),
    ("sleet", "Nieve"),
    ("ice", "Nieve"),
    ("blizzard", "Nieve"),
    ("drizzle", "Llovizna"),
    ("rain", "Lluvia"),
    ("fog", "Neblina"),
    ("mist", "Neblina"),
    ("overcast", "Nublado"),
    ("cloud", "Nublado"),
    ("sun", "Despejado"),
    ("clear", "Despejado"),
]

# Open-Meteo: códigos WMO de current.weather_code
OPEN_METEO_CODE_TRANSLATIONS = {
    0: "Despejado",
    1: "Parcialmente nublado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina",
    51: "Llovizna",
    53: "Llovizna",
    55: "Llovizna",
    56: "Llovizna",
    57: "Llovizna",
    61: "Lluvia",
    63: "Lluvia",
    65: "Lluvia",
    66: "Lluvia",
    67: "Lluvia",
    71: "Nieve",
    73: "Nieve",
    75: "Nieve",
    77: "Nieve",
    80: "Lluvia",
    81: "Lluvia",
    82: "Lluvia",
    85: "Nieve",
    86: "Nieve",
    95: "Tormenta",
    96: "Tormenta",
    99: "Tormenta",
}

DESCONOCIDO = "Desconocido"


def translate_weatherapi(text: str) -> str:
    key = (text or "").strip().lower()
    if key in WEATHERAPI_CONDITION_TRANSLATIONS:
        return WEATHERAPI_CONDITION_TRANSLATIONS[key]
    for keyword, value in _WEATHERAPI_KEYWORDS:
        if keyword in key:
            return value
    return DESCONOCIDO


def translate_open_meteo(code: int) -> str:
    return OPEN_METEO_CODE_TRANSLATIONS.get(code, DESCONOCIDO)
