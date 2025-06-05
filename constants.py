from enum import Enum

class Categoria(Enum):
    PELICULAS = "peliculas"
    SERIES = "series"
    INFANTIL = "infantil"

BASE_URL = "https://play.mercadolibre.com.ar"
REFERER_URL = f"{BASE_URL}/"
API_URL = f"{BASE_URL}/api/"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0'