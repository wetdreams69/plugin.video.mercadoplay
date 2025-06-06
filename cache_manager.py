import os
import json
import time
import xbmc
import xbmcaddon
from xbmcvfs import translatePath

class CacheManager:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.cache_dir = translatePath(self.addon.getAddonInfo('profile'))
        self.cache_file = os.path.join(self.cache_dir, 'addon_cache.json')
        self.ttl_config = {
            'fetch_category_data': 1800,
            'fetch_video_details': 43200,
            'csrf_token': 86400,
            'default': 3600
        }
        self.max_size = 100
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            xbmc.log(f"[ERROR DE CACHÉ] Fallo al cargar: {str(e)}", xbmc.LOGERROR)
            return {}

    def _save_cache(self, data):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            xbmc.log(f"[ERROR DE CACHÉ] Fallo al guardar: {str(e)}", xbmc.LOGERROR)

    def _make_key(self, func_name, *args):
        return f"{func_name}-{'-'.join(str(arg) for arg in args)}"

    def get(self, func_name, *args):
        key = self._make_key(func_name, *args)
        cache = self._load_cache()
        
        if key in cache:
            entry = cache[key]
            ttl = self.ttl_config.get(func_name, self.ttl_config['default'])
            if time.time() - entry['timestamp'] < ttl:
                xbmc.log(f"[CACHÉ EXITOSO] {key}", xbmc.LOGDEBUG)
                return entry['data']
            del cache[key]
            self._save_cache(cache)
        return None

    def set(self, func_name, data, *args):
        key = self._make_key(func_name, *args)
        cache = self._load_cache()
        
        if len(cache) >= self.max_size:
            oldest_key = min(list(cache.keys()), key=lambda k: cache[k]['timestamp'])
            del cache[oldest_key]
        
        cache[key] = {'timestamp': time.time(), 'data': data}
        self._save_cache(cache)
        xbmc.log(f"[CACHÉ GUARDADO] {key}", xbmc.LOGDEBUG)