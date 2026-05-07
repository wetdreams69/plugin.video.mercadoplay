import requests
import xbmc
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, urljoin
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
        key = f"category_data:{category}:{offset}:{limit}"
        cached = self.cache.get(key)
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
            self.cache.set(key, data, ttl=43200)
            return data
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Categoría {category}: {str(e)}", xbmc.LOGERROR)
            return {"components": []}

    def _extract_json_from_html(self, html):
        pattern = r'_n\.ctx\.s\.q\(\s*"(.*?)"\s*\)'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            xbmc.log("[DEBUG] No se encontró el patrón _n.ctx.s.q", xbmc.LOGDEBUG)
            return None
        
        escaped_json = match.group(1)
        try:
            # Reemplazar saltos de línea literales por escapes para que json.loads no falle
            escaped_json = escaped_json.replace('\n', '\\n').replace('\r', '\\r')
            unescaped = json.loads(f'"{escaped_json}"')
        except Exception as e:
            xbmc.log(f"[DEBUG] Error al desescapar JSON: {str(e)}", xbmc.LOGDEBUG)
            unescaped = escaped_json.replace('\\"', '"').replace('\\\\', '\\')
            
        start_idx = unescaped.find('{"pageProps":')
        if start_idx == -1:
            start_idx = unescaped.find('{')
            if start_idx == -1:
                xbmc.log("[DEBUG] No se encontró el inicio del objeto JSON", xbmc.LOGDEBUG)
                return None
        
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
        
        def clean_val(m):
            prefix = m.group(1)
            val = m.group(2)
            if val in ['true', 'false', 'null']:
                return m.group(0)
            return prefix + 'null'

        # Limpieza de símbolos (u, $0, @1, etc.)
        full_json = re.sub(r'([:,\x5b])\s*([a-zA-Z\$@][\w\$@]*)', clean_val, full_json)
        full_json = re.sub(r',\s*}', '}', full_json)
        full_json = re.sub(r',\s*]', ']', full_json)
        
        try:
            return json.loads(full_json)
        except json.JSONDecodeError as e:
            xbmc.log(f"[ERROR DE API] Error final al parsear JSON: {str(e)}", xbmc.LOGERROR)
            return None

    def fetch_video_details(self, video_id):
        key = f"video_details:{video_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        
        url = f"{self.BASE_URL}/ver/{video_id}"
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': self.REFERER_URL,
        }
        
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = self._extract_json_from_html(response.text)
            
            if data:
                # Intentamos devolver pageProps, que contiene toda la metadata necesaria
                page_props = data.get('pageProps', {})
                if page_props:
                    # Si pageProps está muy vacío, intentamos buscar una estructura con 'components'
                    if not page_props.get('components'):
                        def find_container(obj):
                            if isinstance(obj, dict):
                                if 'components' in obj: return obj
                                for v in obj.values():
                                    res = find_container(v)
                                    if res: return res
                            elif isinstance(obj, list):
                                for item in obj:
                                    res = find_container(item)
                                    if res: return res
                            return None
                        
                        result = find_container(page_props)
                        if result:
                            self.cache.set(key, result, ttl=43200)
                            return result
                    
                    self.cache.set(key, page_props, ttl=43200)
                    return page_props
                
                self.cache.set(key, data, ttl=43200)
                return data
            
            csrf_token = self.cache.get('csrf_token') or self.fetch_csrf_token()
            vcp_id = video_id.split('/')[-1]
            api_url = f"{self.API_URL}vcp/{vcp_id}"
            api_headers = {
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
            
            response = self.session.get(api_url, params=params, headers=api_headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            self.cache.set(key, result, ttl=43200)
            return result
            
        except Exception as e:
            xbmc.log(f"[ERROR DE API] Video {video_id}: {str(e)}", xbmc.LOGERROR)
            return None

    def fetch_season_episodes(self, season_id):
        key = f"season_episodes:{season_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        csrf_token = self.cache.get('csrf_token')
        if not csrf_token:
            csrf_token = self.fetch_csrf_token()
        
        if not csrf_token:
            xbmc.log("[ERROR DE AUTENTICACIÓN] No se pudo obtener token CSRF", xbmc.LOGERROR)
            return False

        url = f"{self.API_URL}season/{season_id}"

        headers = {
            'User-Agent': self.USER_AGENT,
            'Referer': self.REFERER_URL,
            'x-csrf-token': csrf_token,
        }
        

        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            text = response.text
            if text.startswith('0:'):
                text = text[2:]
            data = json.loads(text)
            self.cache.set(key, data, ttl=43200)
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
                self.cache.set('csrf_token', token, ttl=86400)
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
        csrf_token = self.cache.get('csrf_token')
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
        key = f"playback_data:{video_id}"
        cached = self.cache.get(key)
        if cached is not None and cached.get('dash_url') not in (None, 'N/A', ''):
            if '0-480' in str(cached.get('dash_url')):
                return cached
            else:
                self.cache.set(key, None, ttl=1)
        
        try:
            player_url = f"{self.BASE_URL}/ver/{video_id}/player?origin=organic"
            
            headers = {
                'User-Agent': self.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,es-AR;q=0.8,es;q=0.7',
                'Referer': f"{self.BASE_URL}/ver/{video_id}",
            }
            
            response = self.session.get(player_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = self._extract_json_from_html(response.text)
            
            if not data:
                raise Exception("No se pudo extraer JSON del HTML")
            
            def find_playback_content(obj):
                if isinstance(obj, dict):
                    if 'playbackContent' in obj:
                        return obj['playbackContent']
                    for v in obj.values():
                        res = find_playback_content(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_playback_content(item)
                        if res: return res
                return None

            playback_content = find_playback_content(data)
            
            if not playback_content:
                xbmc.log(f"[ERROR DE API] No se encontró playbackContent en el JSON", xbmc.LOGERROR)
                raise Exception("No se pudo acceder a los datos de reproducción")
            source = playback_content.get('source', {})
            
            session_init_url = source.get('sessionInitUrl')
            body_payload = source.get('bodyPayload')
            
            dash_url = source.get('dash')
            if dash_url == "N/A" or not dash_url:
                dash_url = None
            
            hls_url = None

            if not dash_url and session_init_url and body_payload:
                try:
                    headers_post = {
                        'User-Agent': self.USER_AGENT,
                        'Content-Type': 'application/json',
                        'Origin': self.BASE_URL,
                        'Referer': player_url,
                    }
                    
                    if 'adSignaling' in body_payload:
                        body_payload['adSignaling']['enabled'] = True
                    
                    if 'adsParams' in body_payload:
                        body_payload['adsParams']['monetization_type'] = 'FREE'
                        body_payload['adsParams']['device_os'] = 'desktop'
                        body_payload['adsParams']['device_type'] = '2'
                        body_payload['adsParams']['platform_id'] = 'desktop'
                        body_payload['adsParams']['allcues'] = '1'
                    
                    if "aws.manifestfilter" in session_init_url:
                        session_init_url = re.sub(r'video_height%3A0-\d+', 'video_height%3A0-480', session_init_url)
                    else:
                        sep = '&' if '?' in session_init_url else '?'
                        session_init_url += f"{sep}aws.manifestfilter=video_height%3A0-480"
                    
                    parsed = urlparse(session_init_url)
                    base_ssai_domain = f"{parsed.scheme}://{parsed.netloc}"

                    post_res_dash = self.session.post(session_init_url, headers=headers_post, json=body_payload, timeout=10)
                    if post_res_dash.status_code == 200:
                        manifest_path = post_res_dash.json().get('manifestUrl')
                        if manifest_path:
                            dash_url = urljoin(base_ssai_domain, manifest_path)

                except Exception as e:
                    xbmc.log(f"[ADVERTENCIA DE API] Error en handshake SSAI: {str(e)}", xbmc.LOGWARNING)
                
            result = {
                'dash_url': dash_url,
                'hls_url': hls_url,
                'license_url': source.get('drm', {}).get('widevine', {}).get('LA_URL'),
                'license_headers': source.get('drm', {}).get('widevine', {}).get('headers', {}),
                'subtitles': playback_content.get('subtitles', []),
                'playback_session_id': playback_content.get('playbackSessionId'),
                'title': playback_content.get('title'),
                'chapters': playback_content.get('chapters', []),
            }
            
            self.cache.set(key, result, ttl=600)
            return result
            
        except Exception as e:
            xbmc.log(f"[ERROR DE API] fetch_playback_data {video_id}: {str(e)}", xbmc.LOGERROR)
            return None