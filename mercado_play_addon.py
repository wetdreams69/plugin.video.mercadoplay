import os
import json
import urllib.parse
import requests
import xbmc
import xbmcgui
import xbmcaddon
from urllib.parse import urlencode
from constants import Categoria, BASE_URL, API_URL, REFERER_URL, USER_AGENT
from kodi_content_handler import KodiContentHandler
from api_client import APIClient
from cache_manager import CacheManager
from cookie_manager import CookieManager
from xbmcvfs import translatePath

class MercadoPlayAddon:
    def __init__(self, addon_handle):
        self.addon_handle = addon_handle
        self.kodi = KodiContentHandler(addon_handle)
        self.cache = CacheManager()
        self.addon = xbmcaddon.Addon()

        # Configurar sistema de cookies
        addon_profile = translatePath(self.addon.getAddonInfo('profile'))
        self.cookie_manager = CookieManager(addon_profile)

        # Configurar sesión HTTP
        self.session = requests.Session()
        self.session.cookies = self.cookie_manager.get_jar()

        # Configurar cliente API
        self.api_client = APIClient(
            session=self.session,
            cache=self.cache,
            user_agent=USER_AGENT,
            base_url=BASE_URL,
            api_url=API_URL,
            referer_url=REFERER_URL
        )

    def list_categories(self):
        xbmc.log("[DEBUG] Entrando en list_categories", xbmc.LOGERROR)
        for category in Categoria:
            url = self.kodi.build_url({'action': 'list_content', 'category': category.value})
            li = self.kodi.create_list_item(category.name.title())
            self.kodi.add_directory_item(url, li)
        self.kodi.end_directory()

    def list_category_content(self, category_str, offset=0, limit=24):
        data = self.api_client.fetch_category_data(category_str, offset, limit)
        
        if not data or "components" not in data:
            xbmcgui.Dialog().notification("Sin contenido", f"No hay resultados para {categoria_str}", xbmcgui.NOTIFICATION_INFO)
            self.kodi.end_directory(self.addon_handle)
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
                "description": media_card.get("description", {}).get("overview", {}).get("props", {}).get("label", "")
            }
            results.append(parsed)

        # Mostrar en Kodi
        for item in results:
            try:
                title = item.get("title", "Sin título")
                link = item.get("url", "")
                image = item.get("image", "")
                description = item.get("description","")

                if not link:
                    continue

                video_id = os.path.basename(urllib.parse.urlparse(link).path).split('?')[0]

                if image and not image.startswith('http'):
                    image = f'https:{image}'

                url = self.kodi.build_url({'action': 'show_details', 'id': video_id})
                li = xbmcgui.ListItem(label=title)
                li.setArt({'thumb': image, 'icon': image, 'poster': image})
                li.setInfo('video', {'title': title, 'episodeguide': description})
                self.kodi.add_directory_item(handle=self.addon_handle, url=url, listitem=li, isFolder=False)
            except Exception as e:
                xbmc.log(f"[ERROR] Item processing failed: {str(e)}", xbmc.LOGERROR)


        # Botón "Ver más" si hay nextPage
        next_page = data.get("nextPage")
        if next_page:
            next_offset = next_page.get("offset")
            next_limit = next_page.get("limit")

            url = self.kodi.build_url({
                'action': 'list_content',
                'categoria': category_str,
                'offset': next_offset,
                'limit': next_limit
            })

            li = xbmcgui.ListItem(label=">> Ver más")
            li.setArt({'thumb': '', 'icon': '', 'poster': ''})
            li.setInfo('video', {'title': 'Ver más contenido'})
            self.kodi.add_directory_item(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        self.kodi.end_directory(self.addon_handle)
        

    
    def list_seasons(self, series_id):
        xbmc.log(f"[DEBUG] Entrando en list_seasons con series_id={series_id}", xbmc.LOGERROR)
        data = self.api_client.fetch_video_details(series_id)

        seasons_selector = data.get("components", {}).get("seasons-selector", {})
        tabs = seasons_selector.get("selector", {}).get("props", {}).get("tabs", [])
        seasons_metadata = seasons_selector.get("seasonsMetadata", [])

        if not tabs:
            xbmc.log("[DEBUG] No se encontraron tabs de temporadas", xbmc.LOGERROR)
            self.kodi.show_notification("Sin temporadas", "Este contenido no tiene temporadas", xbmcgui.NOTIFICATION_WARNING)
            self.kodi.end_directory()
            return

        metadata_map = {s['id']: s for s in seasons_metadata}

        for tab in tabs:
            season_id = tab.get("value")
            season_number = tab.get("label", "0")
            metadata = metadata_map.get(season_id, {})

            title = f"Temporada {season_number}"
            if "episodesCount" in metadata:
                title += f" ({metadata['episodesCount']} episodios)"

            xbmc.log(f"[DEBUG] Agregando temporada: {title}, id: {season_id}", xbmc.LOGERROR)
            url = self.kodi.build_url({'action': 'list_episodes', 'id': season_id})
            li = self.kodi.create_list_item(title)
            li.setProperty('IsPlayable', 'false')
            self.kodi.add_directory_item(url, li, is_folder=True)

        self.kodi.end_directory()

    def list_episodes(self, season_id):
        xbmc.log(f"[DEBUG] Entrando en list_episodes con season_id={season_id}", xbmc.LOGERROR)
        try:
            data = self.api_client.fetch_season_episodes(season_id)
        except Exception as e:
            xbmc.log(f"[ERROR] No se pudo obtener episodios para temporada {season_id}: {str(e)}", xbmc.LOGERROR)
            self.kodi.show_notification("Error", "No se pudieron obtener los episodios", xbmcgui.NOTIFICATION_ERROR)
            self.kodi.end_directory()
            return

        episodes = data.get("props", {}).get("components", [])
        if not episodes:
            xbmc.log("[DEBUG] No se encontraron episodios en la respuesta", xbmc.LOGERROR)
            self.kodi.show_notification("Sin episodios", "No se encontraron episodios disponibles", xbmcgui.NOTIFICATION_INFO)
            self.kodi.end_directory()
            return

        for episode in episodes:
            if episode.get("type") != "compact-media-card":
                continue

            props = episode.get("props", {})
            episode_id = props.get("contentId", "")
            metadata = props.get("linkTo", {}).get("state", {}).get("metadata", {})
            header = props.get("header", {}).get("default", {})

            title = metadata.get("title", "Episodio")
            if header.get("bottomLeftItems"):
                label = header["bottomLeftItems"][0].get("props", {}).get("label")
                if label:
                    title = label

            image = header.get("background", {}).get("props", {}).get("url", "")
            if image and not image.startswith("http"):
                image = f"https:{image}"

            xbmc.log(f"[DEBUG] Agregando episodio: {title}, id: {episode_id}", xbmc.LOGERROR)
            url = self.kodi.build_url({'action': 'show_details', 'id': episode_id})
            li = self.kodi.create_list_item(title)
            li.setArt({'thumb': image, 'icon': image, 'poster': image})
            li.setProperty('IsPlayable', 'true')
            self.kodi.add_directory_item(url, li, is_folder=False)

        self.kodi.end_directory()

    def is_series(self, metadata):
        if not metadata:
            return False

        # 1. Tipo de contenido explícito
        if metadata.get("contentType", "").lower() == "serie":
            return True

        # 2. Heurística por título (ej: "T1:E3", "Temporada 1", etc.)
        title = metadata.get("title", "").lower()
        if "temporada" in title or ("t" in title and "e" in title and ":" in title):
            return True

        return False

    def play_video(self, video_id):
        try:
            if not self.api_client.set_user_preferences():
                xbmc.log("[ADVERTENCIA DE AUTENTICACIÓN] Preferencias de usuario no configuradas", xbmc.LOGWARNING)

            data = self.api_client.fetch_video_details(video_id)
            if not data:
                raise Exception("Datos del video no disponibles")

            player_data = data.get('components', {}).get('player', {})
            if player_data.get('restricted') and not self.addon.getSettingBool('adult_content'):
                self.kodi.show_notification("Contenido restringido", "Habilita +18 en los ajustes para ver este contenido", xbmcgui.NOTIFICATION_WARNING)
                return

            playback = player_data.get('playbackContext', {})
            sources = playback.get('sources', {})
            subtitles = playback.get('subtitles', [])
            drm_data = playback.get('drm', {}).get('widevine', {})

            stream_url = sources.get('dash')
            license_url = drm_data.get('serverUrl')
            http_headers = drm_data.get('httpRequestHeaders', {})
            license_key = http_headers.get('x-dt-auth-token') or http_headers.get('X-AxDRM-Message')

            if not stream_url:
                raise Exception("URL del stream no disponible")
            if not license_url or not license_key:
                raise Exception("Datos DRM incompletos")

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

            li = xbmcgui.ListItem(path=stream_url)
            li.setProperty('inputstream', 'inputstream.adaptive')
            li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            if subtitle_list:
                li.setSubtitles([sub['url'] for sub in subtitle_list])

            if http_headers.get('x-dt-auth-token'):
                license_headers['x-dt-auth-token'] = http_headers.get('x-dt-auth-token')
                license_config = {
                    'license_server_url': license_url.replace("specConform=true", ""),
                    'headers': urlencode(license_headers),
                    'post_data': 'R{SSM}',
                    'response_data': 'JBlicense'
                }
                li.setProperty('inputstream.adaptive.license_key', '|'.join(license_config.values()))
            elif http_headers.get('X-AxDRM-Message'):
                license_headers['X-AxDRM-Message'] = http_headers.get('X-AxDRM-Message')
                license_config = license_url + '|' + 'X-AxDRM-Message=' + license_key + '|R{SSM}|'
                li.setProperty('inputstream.adaptive.license_key', license_config)

            li.setMimeType('application/dash+xml')
            li.setContentLookup(False)
            self.kodi.resolve_url(True, li)

        except Exception as e:
            xbmc.log(f"[ERROR DE REPRODUCCIÓN] {str(e)}", xbmc.LOGERROR)
            self.kodi.show_notification("Error de reproducción", str(e), xbmcgui.NOTIFICATION_ERROR)
            self.kodi.resolve_url(False, self.kodi.create_list_item())

    def router(self, paramstring):
        params = dict(urllib.parse.parse_qsl(paramstring)) if paramstring else {}
        action = params.get('action')

        if not action:
            self.list_categories()
        elif action == 'list_content':
            category = params.get('category')
            offset = int(params.get('offset', 0))
            limit = int(params.get('limit', 24))
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
        else:
            xbmc.log(f"[ROUTER] Acción desconocida: {action}", xbmc.LOGWARNING)

    def run(self, argv):
        paramstring = argv[2][1:] if len(argv) > 2 else None
        self.router(paramstring)
        self.cookie_manager.save_cookies()
