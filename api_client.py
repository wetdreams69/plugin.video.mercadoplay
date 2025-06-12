import requests
import xbmc
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from constants import USER_AGENT, BASE_URL, API_URL, REFERER_URL

class APIClient:
    def __init__(self, session, cache, user_agent=USER_AGENT, base_url=BASE_URL, api_url=API_URL, referer_url=REFERER_URL):
        self.session = session
        self.cache = cache
        self.USER_AGENT = user_agent
        self.BASE_URL = base_url
        self.API_URL = api_url
        self.REFERER_URL = referer_url

    def fetch_category_data(self, category, offset=0, limit=24):
        cached = self.cache.get('fetch_category_data', category, offset, limit)
        if cached is not None:
            return cached
        
        params = {"filter": category, "version": ""}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit

        url = f"{self.API_URL}feed?{urlencode(params)}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": self.REFERER_URL
        }

        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache.set('fetch_category_data', data, category)
            return data
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Categoría {category}: {str(e)}", xbmc.LOGERROR)
            return {"components": []}

    def fetch_video_details(self, video_id):
        cached = self.cache.get('fetch_video_details', video_id)
        if cached is not None:
            return cached
        
        csrf_token = self.cache.get('csrf_token')
        if not csrf_token:
            csrf_token = self.fetch_csrf_token()

        url = f"{self.API_URL}vcp/{video_id}"

        headers = {
            'User-Agent': self.USER_AGENT,
            'Referer': self.REFERER_URL,
            'X-CSRF-Token': csrf_token if csrf_token else ''
        }
        
        params = {
            'origin': 'mplay_hub',
            'origin_position': '0',
            'origin_name_carousel': 'main-slider',
            'origin_carousel': 'vertical_media_card_l',
            'origin_position_carousel': '1',
            'origin_filter': 'no_filter',
        }

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache.set('fetch_video_details', data, video_id)
            return data
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Video {video_id}: {str(e)}", xbmc.LOGERROR)
            return None

    def fetch_season_episodes(self, season_id):
        cached = self.cache.get('fetch_season_episodes', season_id)
        if cached is not None:
            return cached

        csrf_token = self.cache.get('csrf_token','')
        if not csrf_token:
            csrf_token = self.fetch_csrf_token()
        
        if not csrf_token:
            xbmc.log("[ERROR DE AUTENTICACIÓN] No se pudo obtener token CSRF", xbmc.LOGERROR)
            return False

        url = f"{self.API_URL}/seasons/{season_id}/episodes"

        headers = {
            'User-Agent': self.USER_AGENT,
            'Referer': self.REFERER_URL,
            'x-csrf-token': csrf_token,
        }
        

        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            self.cache.set('fetch_season_episodes', data, season_id)
            return response.json()
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Obtener temporada {season_id}: {str(e)}", xbmc.LOGERROR)
            return None

    def fetch_csrf_token(self):
        cached = self.cache.get('csrf_token')
        if cached is not None:
            return cached
        try:
            headers = {
                'User-Agent': self.USER_AGENT,
                'Referer': self.REFERER_URL
            }

            token_response = self.session.get(self.BASE_URL, headers=headers)
            soup = BeautifulSoup(token_response.text, 'html.parser')
            meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
            token = meta_tag['content'] if meta_tag and meta_tag.has_attr('content') else None

            if token:
                self.cache.set('csrf_token', token)
                xbmc.log(f"[DEBUG] Token CSRF obtenido: {token}", xbmc.LOGDEBUG)
            return token
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Fallo al obtener token CSRF: {str(e)}", xbmc.LOGERROR)
            return None

    def set_user_preferences(self):
        csrf_token = self.cache.get('csrf_token','')
        if not csrf_token:
            csrf_token = self.fetch_csrf_token()
        
        if not csrf_token:
            xbmc.log("[ERROR DE AUTENTICACIÓN] No se pudo obtener token CSRF", xbmc.LOGERROR)
            return False
        
        url = f"{self.API_URL}user-preferences"

        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': self.REFERER_URL,
            'Content-Type': 'application/json',
            'x-csrf-token': csrf_token,
            'Origin': self.BASE_URL
        }
        
        body = {
            'content_access_confirmation': 'accepted'
        }

        try:
            response = self.session.put(url, headers=headers, json=body, timeout=10)
            
            if response.status_code == 200:
                xbmc.log("[AUTENTICACIÓN EXITOSA] Preferencias de usuario configuradas", xbmc.LOGINFO)
                return True
            elif response.status_code == 403:
                xbmc.log("[ERROR DE AUTENTICACIÓN] 403 Prohibido - Usuario no autenticado", xbmc.LOGWARNING)
                return False
            elif response.status_code == 401:
                xbmc.log("[ERROR DE AUTENTICACIÓN] 401 No autorizado - Token inválido", xbmc.LOGWARNING)
                return False
            else:
                xbmc.log(f"[ERROR DE AUTENTICACIÓN] Código inesperado: {response.status_code} - {response.text}", xbmc.LOGWARNING)
                return False
                
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Preferencias de usuario: {str(e)}", xbmc.LOGERROR)
            return False