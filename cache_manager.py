import os
import json
import time
import hashlib
import xbmc
import xbmcaddon
from xbmcvfs import translatePath

class CacheManager:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.cache_dir = translatePath(self.addon.getAddonInfo('profile'))
        self.ttl_config = {
            'fetch_category_data': 43200,
            'fetch_video_details': 43200,
            'fetch_season_episodes': 43200,
            'csrf_token': 86400,
            'default': 3600
        }
        self.max_files = 1000
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _make_key(self, func_name, *args):
        raw_key = f"{func_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(raw_key.encode()).hexdigest()

    def _get_cache_path(self, key):
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, func_name, *args):
        key = self._make_key(func_name, *args)
        path = self._get_cache_path(key)

        if not os.path.exists(path):
            return None

        try:
            with open(path, 'r') as f:
                entry = json.load(f)
            ttl = self.ttl_config.get(func_name, self.ttl_config['default'])
            if time.time() - entry['timestamp'] < ttl:
                return entry['data']
            os.remove(path)
        except Exception as e:
            xbmc.log(f"[ERROR DE CACHÉ] Fallo en get(): {str(e)}", xbmc.LOGERROR)
        return None

    def set(self, func_name, data, *args):
        key = self._make_key(func_name, *args)
        path = self._get_cache_path(key)

        entry = {
            'timestamp': time.time(),
            'data': data
        }

        try:
            with open(path, 'w') as f:
                json.dump(entry, f)
        except Exception as e:
            xbmc.log(f"[ERROR DE CACHÉ] Fallo en set(): {str(e)}", xbmc.LOGERROR)

        self._enforce_cache_limit()

    def _enforce_cache_limit(self):
        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        if len(files) <= self.max_files:
            return

        full_paths = [(f, os.path.getmtime(os.path.join(self.cache_dir, f))) for f in files]
        full_paths.sort(key=lambda x: x[1])  # más viejo primero
        for f, _ in full_paths[:len(files) - self.max_files]:
            try:
                os.remove(os.path.join(self.cache_dir, f))
            except Exception as e:
                xbmc.log(f"[ERROR DE CACHÉ] No se pudo borrar archivo viejo: {str(e)}", xbmc.LOGERROR)

    def clear(self):
        try:
            for f in os.listdir(self.cache_dir):
                if f.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, f))
        except Exception as e:
            xbmc.log(f"[ERROR DE CACHÉ] Fallo al borrar caché: {str(e)}", xbmc.LOGERROR)
