import os
import json
import urllib.parse
import requests
import xbmc
import xbmcgui
import xbmcaddon
from urllib.parse import urlencode
from constants import Categoria, BASE_URL, API_URL, REFERER_URL, USER_AGENT, SUBCATEGORIES
from kodi_content_handler import KodiContentHandler
from api_client import APIClient
from cacheman import CacheManager
from cookie_manager import CookieManager
from xbmcvfs import translatePath
from inputstreamhelper import Helper
from adskipper import start_ad_skipper

class MercadoPlayAddon:
    def __init__(self, addon_handle):
        self.addon_handle = addon_handle
        self.kodi = KodiContentHandler(addon_handle)
        self.cache = CacheManager(
            db_name='mercadoplay_cache.db',
            compress=True,
            compress_threshold=2048
        )
        self.addon = xbmcaddon.Addon()

        addon_profile = translatePath(self.addon.getAddonInfo('profile'))
        self.cookie_manager = CookieManager(addon_profile)

        self.session = requests.Session()
        self.session.cookies = self.cookie_manager.get_jar()

        self.api_client = APIClient(
            session=self.session,
            cache=self.cache,
            user_agent=USER_AGENT,
            base_url=BASE_URL,
            api_url=API_URL,
            referer_url=REFERER_URL
        )

    def list_categories(self):
        for category in Categoria:
            url = self.kodi.build_url({'action': 'list_content', 'category': category.value})
            li = self.kodi.create_list_item(category.name.title())
            self.kodi.add_directory_item(url, li)
        self.kodi.end_directory()

    def list_category_content(self, category_str, offset=0, limit=24):
        data = self.api_client.fetch_category_data(category_str, offset, limit)
        
        if not data or "components" not in data:
            xbmcgui.Dialog().notification("Sin contenido", f"No hay resultados para {category_str}", xbmcgui.NOTIFICATION_INFO)
            self.kodi.end_directory()
            return

        results = []
        
        for component in data.get("components", []):
            if component.get("type") != "media-card":
                continue

            media_card = component.get("props",{})
            parsed = {
                "title": media_card.get("linkTo", {}).get("state", {}).get("metadata", {}).get("title", "").replace(" - Mercado Play", ""),
                "url": media_card.get("linkTo", {}).get("pathname", ""),
                "image": media_card.get("header", {}).get("default", {}).get("background", {}).get("props", {}).get("url", ""),
                "subtitle": media_card.get("description", {}).get("subtitle", ""),
                "description": media_card.get("description", {}).get("overview", {}).get("props", {}).get("label", ""),
                "media_card": media_card
            }
            results.append(parsed)

        for item in results:
            try:
                title = item.get("title", "Sin título")
                link = item.get("url", "")
                image = item.get("image", "")
                description = item.get("description","")

                if not link:
                    continue

                video_id = urllib.parse.urlparse(link).path.split('/ver/')[-1].split('?')[0].strip('/')

                if image and not image.startswith('http'):
                    image = f'https:{image}'

                try:
                    media_card = item.get("media_card")
                    if self.is_series(media_card):
                        action = 'list_seasons'
                    else:
                        action = 'show_details'
                except Exception as e:
                    xbmc.log(f"[ERROR] No se pudo determinar si es serie: {e}", xbmc.LOGWARNING)
                    action = 'show_details'

                url = self.kodi.build_url({'action': action, 'id': video_id})
                li = xbmcgui.ListItem(label=title)
                li.setArt({'thumb': image, 'icon': image, 'poster': image})
                li.setInfo('video', {'title': title, 'plot': description})
                is_folder = action == 'list_seasons'

                if not is_folder:
                    li.setProperty('IsPlayable', 'true')
                    li.setPath(url)
                self.kodi.add_directory_item(url, li, is_folder)

            except Exception as e:
                xbmc.log(f"[ERROR] Item processing failed: {str(e)}", xbmc.LOGERROR)


        next_page = data.get("nextPage")
        if next_page:
            next_offset = next_page.get("offset")
            next_limit = next_page.get("limit")

            url = self.kodi.build_url({
                'action': 'list_content',
                'category': category_str,
                'offset': next_offset,
                'limit': next_limit
            })

            li = xbmcgui.ListItem(label=">> Ver más")
            li.setArt({'thumb': '', 'icon': '', 'poster': ''})
            li.setInfo('video', {'title': 'Ver más contenido'})
            self.kodi.add_directory_item(url, li, True)

        self.kodi.end_directory()
        

    
    def list_seasons(self, series_id):
        data = self.api_client.fetch_video_details(series_id)
        if not data:
            self.kodi.show_notification("Error", "No se pudo obtener información de la serie", xbmcgui.NOTIFICATION_ERROR)
            self.kodi.end_directory()
            return

        components = data.get("components", [])
        seasons_selector = {}
        tabs = []
        
        # Estilo 1: Basado en componentes (Nordic)
        if isinstance(components, dict):
            seasons_selector = components.get("seasons-selector", {})
        elif isinstance(components, list):
            for comp in components:
                if comp.get("type") == "seasons-selector":
                    seasons_selector = comp
                    break
        
        if seasons_selector:
            tabs = seasons_selector.get("selector", {}).get("props", {}).get("tabs", [])
            if not tabs:
                seasons_metadata = seasons_selector.get("seasonsMetadata", [])
                if seasons_metadata:
                    tabs = [{"value": s["id"], "label": s.get("name", str(i+1))} for i, s in enumerate(seasons_metadata)]
            
            seasons_metadata = seasons_selector.get("seasonsMetadata", [])
            metadata_map = {s['id']: s for s in seasons_metadata}

            for tab in tabs:
                season_id = tab.get("value")
                season_number = tab.get("label", "0")
                metadata = metadata_map.get(season_id, {})

                title = f"Temporada {season_number}"
                if "episodesCount" in metadata:
                    title += f" ({metadata['episodesCount']} episodios)"

                url = self.kodi.build_url({'action': 'list_episodes', 'id': season_id})
                li = self.kodi.create_list_item(title)
                li.setProperty('IsPlayable', 'false')
                self.kodi.add_directory_item(url, li, is_folder=True)
        
        # Estilo 2: Basado en data.seasons (Estructura simplificada)
        else:
            inner_data = data.get("data", {})
            seasons = inner_data.get("seasons", [])
            if not seasons and not tabs:
                # Si sigue sin haber nada, intentar buscar 'seasons' en la raíz de data
                seasons = data.get("seasons", [])

            for season in seasons:
                season_id = season.get("id")
                season_number = season.get("index", "0")
                ep_count = season.get("episodesCount")
                
                title = f"Temporada {season_number}"
                if ep_count:
                    title += f" ({ep_count} episodios)"
                
                url = self.kodi.build_url({'action': 'list_episodes', 'id': season_id})
                li = self.kodi.create_list_item(title)
                li.setProperty('IsPlayable', 'false')
                self.kodi.add_directory_item(url, li, is_folder=True)

        if not seasons_selector and not data.get("data", {}).get("seasons") and not data.get("seasons"):
            self.kodi.show_notification("Sin temporadas", "No se encontraron temporadas disponibles", xbmcgui.NOTIFICATION_WARNING)

        self.kodi.end_directory()

    def list_episodes(self, season_id):
        try:
            data = self.api_client.fetch_season_episodes(season_id)
            if not data:
                raise Exception("Respuesta vacía de la API")
        except Exception as e:
            xbmc.log(f"[ERROR] No se pudo obtener episodios para temporada {season_id}: {str(e)}", xbmc.LOGERROR)
            self.kodi.show_notification("Error", "No se pudieron obtener los episodios", xbmcgui.NOTIFICATION_ERROR)
            self.kodi.end_directory()
            return

        # Estilo 1: Nueva API { "content": { "episodes": [...] } }
        content = data.get("content", {})
        episodes = content.get("episodes", [])
        
        if episodes:
            for ep in episodes:
                episode_id = ep.get("id")
                title = ep.get("name", f"Episodio {episode_id[:8]}")
                label = ep.get("episode_label")
                if label:
                    title = f"{label}. {title}"
                
                description = ep.get("description") or ep.get("overview", "")
                
                image = ""
                images = ep.get("images", [])
                for img in images:
                    if img.get("type") == "LANDSCAPE":
                        image = img.get("url", "")
                        break
                if not image and images:
                    image = images[0].get("url", "")
                
                if image and not image.startswith("http"):
                    image = f"https:{image}"

                url = self.kodi.build_url({'action': 'show_details', 'id': f"episodio/{episode_id}"})
                li = self.kodi.create_list_item(title)
                li.setArt({'thumb': image, 'icon': image, 'poster': image})
                li.setInfo('video', {'title': title, 'plot': description})
                li.setProperty('IsPlayable', 'true')
                li.setPath(url)
                self.kodi.add_directory_item(url, li, is_folder=False)
        
        # Estilo 2: API antigua { "props": { "components": [...] } }
        else:
            components = data.get("props", {}).get("components", [])
            if not components:
                self.kodi.show_notification("Sin episodios", "No se encontraron episodios disponibles", xbmcgui.NOTIFICATION_INFO)
                self.kodi.end_directory()
                return

            for episode in components:
                if episode.get("type") != "compact-media-card":
                    continue

                props = episode.get("props", {})
                episode_id = props.get("contentId")
                header = props.get("header", {}).get("default", {})

                title = props.get("title")
                if not title:
                    bottom_left = header.get("bottomLeftItems", [{}])
                    if bottom_left:
                        title = bottom_left[0].get("props", {}).get("label")
                
                if not title:
                    title = f"Episodio {episode_id[:8]}"

                image = header.get("background", {}).get("props", {}).get("url", "")
                if image and not image.startswith("http"):
                    image = f"https:{image}"

                description = props.get("description", {}).get("props", {}).get("label", "")

                url = self.kodi.build_url({'action': 'show_details', 'id': f"episodio/{episode_id}"})
                li = self.kodi.create_list_item(title)
                li.setArt({'thumb': image, 'icon': image, 'poster': image})
                li.setInfo('video', {'title': title, 'plot': description})
                li.setProperty('IsPlayable', 'true')
                li.setPath(url)
                self.kodi.add_directory_item(url, li, is_folder=False)

        self.kodi.end_directory()


    def is_series(self, media_card):
        try:
            components = media_card["linkTo"]["state"]["components"]
            for comp in components:
                if comp.get("type", "").startswith("seasons-selector") and \
                comp.get("props", {}).get("seasons", 0) > 0:
                    return True
        except (KeyError, TypeError):
            pass
        return False


    def play_video(self, video_id):
        is_helper = Helper("mpd", drm='com.widevine.alpha')
        if is_helper.check_inputstream():
            try:
                playback_data = self.api_client.fetch_playback_data(video_id)
                
                playback_session_id = None
                is_hls = False

                if not playback_data:
                    xbmc.log("[ADVERTENCIA] fetch_playback_data falló, intentando fetch_video_details", xbmc.LOGWARNING)
                    if not self.api_client.set_user_preferences():
                        xbmc.log("[ADVERTENCIA DE AUTENTICACIÓN] Preferencias de usuario no configuradas", xbmc.LOGWARNING)

                    data = self.api_client.fetch_video_details(video_id)
                    if not data:
                        raise Exception("Datos del video no disponibles")

                    components = data.get('components', [])
                    player_data = {}
                    if isinstance(components, dict):
                        player_data = components.get('player', {})
                    elif isinstance(components, list):
                        for comp in components:
                            if comp.get('type') == 'player':
                                player_data = comp
                                break
                    
                    if player_data.get('restricted') and not self.addon.getSettingBool('adult_content'):
                        self.kodi.show_notification("Contenido restringido", "Habilita +18 en los ajustes para ver este contenido", xbmcgui.NOTIFICATION_WARNING)
                        return

                    playback = player_data.get('playbackContext', {})
                    if not playback:
                        # Intentar buscar playbackContent directamente si no hay player component
                        playback = data.get('playbackContent', {})
                    
                    sources = playback.get('sources', {}) or playback.get('source', {})
                    subtitles = playback.get('subtitles', [])
                    drm_data = playback.get('drm', {}).get('widevine', {})

                    stream_url = sources.get('sessionInitUrl') or sources.get('dash')
                    if stream_url == "N/A":
                        stream_url = None
                    is_hls = stream_url and ('.m3u8' in stream_url)
                    license_url = drm_data.get('serverUrl')
                    http_headers = drm_data.get('httpRequestHeaders', {})
                    license_key = http_headers.get('x-dt-auth-token') or http_headers.get('X-AxDRM-Message')
                    playback_session_id = playback.get('playbackSessionId')
                else:
                    stream_url = playback_data.get('dash_url') or playback_data.get('hls_url')
                    if stream_url == "N/A":
                        stream_url = None
                    
                    license_url = playback_data.get('license_url')
                    http_headers = playback_data.get('license_headers', {})
                    subtitles = playback_data.get('subtitles', [])
                    license_key = http_headers.get('x-dt-auth-token') or http_headers.get('X-AxDRM-Message')
                    playback_session_id = playback_data.get('playback_session_id')
                    is_hls = stream_url and ('.m3u8' in stream_url)

                if not stream_url:
                    raise Exception("URL del stream no disponible")
                if not license_url:
                    raise Exception("URL de licencia no disponible")

                subtitle_list = []
                for sub in subtitles:
                    lang = sub.get('lang', '')
                    url = sub.get('url', '')
                    if lang and lang != "disabled" and url:
                        display_name = sub.get('label', lang.upper())
                        if lang.lower() == 'es-mx':
                            display_name = "Español (Latinoamérica)"
                        elif lang.lower() == 'pt-br':
                            display_name = "Portugués (Brasil)"
                        elif lang.lower() == 'en-us':
                            display_name = "English"
                        elif lang.lower() == 'es-es':
                            display_name = "Español (España)"
                        subtitle_list.append({
                            'label': display_name,
                            'language': lang,
                            'url': url
                        })

                license_headers = {
                    'User-Agent': USER_AGENT,
                    'Content-Type': 'application/octet-stream',
                    'Origin': BASE_URL,
                    'Referer': REFERER_URL,
                }
                
                if http_headers:
                    for key, value in http_headers.items():
                        existing_keys = {k.lower(): k for k in license_headers.keys()}
                        if key.lower() in existing_keys:
                            license_headers[existing_keys[key.lower()]] = value
                        else:
                            license_headers[key] = value

                if playback_session_id and not any(k.lower() == 'x-dt-auth-token' for k in license_headers):
                    license_headers['x-dt-auth-token'] = playback_session_id

                li = xbmcgui.ListItem(path=stream_url)
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                if subtitle_list:
                    li.setSubtitles([sub['url'] for sub in subtitle_list])
                
                license_headers['Referer'] = REFERER_URL
                
                license_headers_url = urlencode(license_headers)
                
                license_config = {
                    'license_server_url': license_url,
                    'headers': license_headers_url,
                    'post_data': 'R{SSM}',
                    'response_data': ''
                }
                
                license_config_str = '|'.join(license_config.values())
                
                li.setProperty('inputstream.adaptive.license_key', license_config_str)

                if is_hls:
                    li.setMimeType('application/vnd.apple.mpegurl')
                    li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                else:
                    li.setMimeType('application/dash+xml')
                    li.setProperty('inputstream.adaptive.max_video_resolution', '480')

                li.setContentLookup(False)
                xbmc.log(f"[REPRODUCCIÓN] Iniciando reproducción de video ID {video_id} con URL: {stream_url}", xbmc.LOGINFO)

                skipper = None
                thread = None

                if not is_hls and self.addon.getSettingBool('enable_adskipper'):
                    try:
                        skipper, thread = start_ad_skipper(
                            stream_url,
                            label="Mercado Play",
                            extra_headers={
                                "User-Agent": USER_AGENT,
                                "Referer": REFERER_URL
                            }
                        )
                    except Exception as e:
                        xbmc.log(f"[ADSKIPPER] Error al iniciar: {str(e)}", xbmc.LOGWARNING)

                self.kodi.resolve_url(True, li)

                if skipper:
                    monitor = xbmc.Monitor()
                    player = xbmc.Player()
                    
                    for _ in range(100):
                        if player.isPlaying() or monitor.abortRequested():
                            break
                        monitor.waitForAbort(0.1)

                    while player.isPlaying() and not monitor.abortRequested():
                        monitor.waitForAbort(1)

                    skipper.stop()
                    if thread:
                        thread.join(timeout=2)
                    xbmc.log(f"[ADSKIPPER] Finalizado. Ads saltados: {skipper.skip_count}", xbmc.LOGINFO)

            except Exception as e:
                xbmc.log(f"[ERROR DE REPRODUCCIÓN] {str(e)}", xbmc.LOGERROR)
                self.kodi.show_notification("Error de reproducción", str(e), xbmcgui.NOTIFICATION_ERROR)
                self.kodi.resolve_url(False, self.kodi.create_list_item())

    def list_subcategories(self, main_category):
        subcategories = SUBCATEGORIES.get(main_category, [])
        for label, filter_value in subcategories:
            url = self.kodi.build_url({'action': 'list_content', 'category': filter_value})
            li = self.kodi.create_list_item(label)
            self.kodi.add_directory_item(url, li, is_folder=True)
        self.kodi.end_directory()
    
    def router(self, paramstring):
        params = dict(urllib.parse.parse_qsl(paramstring)) if paramstring else {}
        action = params.get('action')

        if not action:
            self.list_categories()
        elif action == 'list_content':
            category = params.get('category')
            offset = int(params.get('offset', 0))
            limit = int(params.get('limit', 24))
            if category in ['peliculas', 'series']:
                self.list_subcategories(category)
            else:
                self.list_category_content(category, offset, limit)
        elif action == 'list_seasons':
            series_id = params.get('id')
            self.list_seasons(series_id)
        elif action == 'list_episodes':
            season_id = params.get('id')
            self.list_episodes(season_id)
        elif action == 'show_details':
            video_id = params.get('id')
            self.play_video(video_id)
        elif action == 'clear_cache':
            self.cache.clear()
            xbmc.executebuiltin('Notification(MercadoLibre Play, Caché borrado con éxito, 3000, info)')
        else:
            xbmc.log(f"[ROUTER] Acción desconocida: {action}", xbmc.LOGWARNING)

    def run(self, argv):
        paramstring = argv[2][1:] if len(argv) > 2 else None
        self.api_client.init()
        self.router(paramstring)
        self.cookie_manager.save_cookies()
