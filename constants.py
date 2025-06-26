from enum import Enum

class Categoria(Enum):
    PELICULAS = "peliculas"
    SERIES = "series"
    INFANTIL = "infantil"

BASE_URL = "https://play.mercadolibre.com.ar"
REFERER_URL = f"{BASE_URL}/"
API_URL = f"{BASE_URL}/api/"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
