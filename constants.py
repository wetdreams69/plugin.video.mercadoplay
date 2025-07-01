from enum import Enum

class Categoria(Enum):
    PELICULAS = "peliculas"
    SERIES = "series"
    INFANTIL = "infantil"

BASE_URL = "https://play.mercadolibre.com.ar"
REFERER_URL = f"{BASE_URL}/"
API_URL = f"{BASE_URL}/api/"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'

SUBCATEGORIES = {
    "peliculas": [
        ("Todas", "peliculas"),
        ("Destacados", "peliculas/destacados"),
        ("Comedia", "peliculas/comedia"),
        ("Acción", "peliculas/accion"),
        ("Ciencia Ficción", "peliculas/ciencia-ficcion"),
        ("Drama", "peliculas/drama"),
        ("Terror", "peliculas/terror"),
        ("Aventura", "peliculas/aventura"),
        ("Familia", "peliculas/familia"),
        ("Romance", "peliculas/romance"),
        ("Documental", "peliculas/documental"),
        ("Crimen", "peliculas/crimen"),
    ],
    "series": [
        ("Todas", "series"),
        ("Destacados", "series/destacados"),
        ("Anime", "series/anime"),
        ("Drama", "series/drama"),
        ("Acción & Aventura", "series/accion_aventura"),
        ("Más Géneros", "series/mas_genero"),
        ("Comedia", "series/comedia"),
        ("Novelas Latinas", "series/novelas_latinas"),
        ("Pasar el rato", "series/pasar_el_rato"),
    ]
}
