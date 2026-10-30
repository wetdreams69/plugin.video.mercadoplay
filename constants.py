from enum import Enum
import xbmcaddon

class Categoria(Enum):
    PELICULAS = "peliculas"
    SERIES = "series"

addon = xbmcaddon.Addon()
country = addon.getSetting('country')

if country == "1":
    BASE_URL = "https://play.mercadolibre.com.co"
else:
    BASE_URL = "https://play.mercadolibre.com.ar"

REFERER_URL = f"{BASE_URL}/"
API_URL = f"{BASE_URL}/api/"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36'

# Grupos del nuevo API /api/groups/{seccion}
# Cada grupo es una colección de contenido con items de tipo MOVIE o SHOW
GRUPOS = {
    "peliculas": [
        ("Destacados", "oscars"),
        ("Nuevos", "new-in-mercado-play"),
        ("Top 10 Películas", "top-10-movie"),
        ("Acción", "genre-x-movie-action"),
        ("Aventura", "genre-x-movie-adventure"),
        ("Comedia", "genre-x-movie-comedy"),
        ("Crimen", "genre-x-movie-crime"),
        ("Drama", "genre-x-movie-drama"),
        ("Fantasía", "genre-x-movie-fantasy"),
        ("Romance", "genre-x-movie-romance"),
        ("Ciencia Ficción", "genre-x-movie-science-fiction"),
        ("Terror", "genre-x-movie-terror"),
        ("Clásicos", "classics-movie"),
        ("Para la familia", "for-the-family-movie"),
    ],
    "series": [
        ("Top 10 Series", "top-10-show"),
        ("Acción", "genre-x-show-action"),
        ("Comedia", "genre-x-show-comedy"),
        ("Drama", "genre-x-show-drama"),
        ("Para pasar el rato", "pass-the-time-show"),
    ],
}

# Mapeo de categoría principal a lista de (label, groupId)
CATEGORIA_GRUPOS = {
    "peliculas": GRUPOS["peliculas"],
    "series": GRUPOS["series"],
}
