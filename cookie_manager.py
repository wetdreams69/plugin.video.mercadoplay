import os
import http.cookiejar
import xbmcaddon
from xbmcvfs import translatePath

class CookieManager:
    def __init__(self, profile_path=None):
        if profile_path is None:
            addon_profile = translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
            self.cookie_file = os.path.join(addon_profile, 'cookies.txt')
        else:
            self.cookie_file = os.path.join(profile_path, 'cookies.txt')
            
        self.cookie_jar = http.cookiejar.LWPCookieJar(self.cookie_file)
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except FileNotFoundError:
            pass

    def get_jar(self):
        return self.cookie_jar

    def save_cookies(self):
        self.cookie_jar.save(ignore_discard=True, ignore_expires=True)