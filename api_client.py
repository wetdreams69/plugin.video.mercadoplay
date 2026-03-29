import requests
import xbmc
import re
import json
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
        
        params = {"filter": category}
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
            'x-csrf-token': csrf_token if csrf_token else ''
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
            data = response.json()
            self.cache.set('fetch_season_episodes', data, season_id)
            return data
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
            return token
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Fallo al obtener token CSRF: {str(e)}", xbmc.LOGERROR)
            return None

    def init(self):
        try:
            headers = {
                'User-Agent': self.USER_AGENT
            }

            response = self.session.get(self.BASE_URL, headers=headers, timeout=10)
            response.raise_for_status()

            xbmc.log("[PING] Cookies actualizadas desde BASE_URL", xbmc.LOGINFO)
            
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Fallo a obtener cookies: {str(e)}", xbmc.LOGERROR)
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

    def fetch_playback_data(self, video_id):
        cached = self.cache.get('fetch_playback_data', video_id)
        if cached is not None:
            return cached
        
        try:
            player_url = f"{self.BASE_URL}/ver/{video_id}/player?origin=organic"
            
            headers = {
                'User-Agent': self.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,es-AR;q=0.8,es;q=0.7',
                'Referer': f"{self.BASE_URL}ver/{video_id}",
            }
            
            response = self.session.get(player_url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text
            
            pattern = r'_n\.ctx\.s\.q\(\s*"((?:[^"\\]|\\.)*)"\s*\)'
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                raise Exception("No se encontró _n.ctx.s.q en el HTML")
            
            escaped_json = match.group(1)
            try:
                unescaped = json.loads(f'"{escaped_json}"')
            except json.JSONDecodeError as e:
                xbmc.log(f"[ERROR DE API] Error al desescapar JSON: {str(e)}", xbmc.LOGERROR)
                raise
            
            start_idx = unescaped.find('{"pageProps":')
            if start_idx == -1:
                start_idx = unescaped.find('{')
                if start_idx == -1:
                    raise Exception("No se encontró ningún objeto JSON")
            
            brace_count = 0
            in_string = False
            escape = False
            end_idx = start_idx
            for i, ch in enumerate(unescaped[start_idx:], start=start_idx):
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"' and not escape:
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
            else:
                end_idx = len(unescaped)
            
            full_json = unescaped[start_idx:end_idx]
            
            full_json = re.sub(r':u\b', ':null', full_json)
            full_json = re.sub(r',u\b', ',null', full_json)
            full_json = re.sub(r'\bu,', 'null,', full_json)
            full_json = re.sub(r',\s*}', '}', full_json)
            full_json = re.sub(r',\s*]', ']', full_json)
            
            try:
                data = json.loads(full_json)
            except json.JSONDecodeError as e:
                xbmc.log(f"[ERROR DE API] Error al parsear JSON: {str(e)}", xbmc.LOGERROR)
                raise
            
            try:
                playback_data = data['pageProps']['dehydratedState']['queries'][0]['state']['data']
            except (KeyError, IndexError, TypeError) as e:
                if isinstance(data, dict) and 'playbackContent' in data:
                    playback_data = data
                else:
                    xbmc.log(f"[ERROR DE API] Estructura JSON inesperada: {str(e)}", xbmc.LOGERROR)
                    raise Exception(f"No se pudo acceder a los datos de reproducción: {e}")
            
            playback_content = playback_data.get('playbackContent', {})
            source = playback_content.get('source', {})
            
            result = {
                'dash_url': source.get('dash'),
                'hls_url': source.get('hls'),
                'license_url': source.get('drm', {}).get('widevine', {}).get('LA_URL'),
                'license_headers': source.get('drm', {}).get('widevine', {}).get('headers', {}),
                'subtitles': playback_content.get('subtitles', []),
                'playback_session_id': playback_content.get('playbackSessionId'),
                'title': playback_content.get('title'),
            }
            
            self.cache.set('fetch_playback_data', result, video_id)
            return result
            
        except Exception as e:
            xbmc.log(f"[ERROR DE API] fetch_playback_data {video_id}: {str(e)}", xbmc.LOGERROR)
            return None