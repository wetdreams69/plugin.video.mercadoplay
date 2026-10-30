"""Fake ``xbmcaddon`` module so the addon can be imported outside Kodi."""

DEFAULT_SETTINGS = {
    "country": "",        # empty -> Argentina (play.mercadolibre.com.ar)
    "adult_content": "false",
    "enable_adskipper": "true",
}


class Addon:
    def __init__(self, addon_id="plugin.video.mercadoplay"):
        self.addon_id = addon_id
        self._settings = dict(DEFAULT_SETTINGS)

    def getSetting(self, key):
        return self._settings.get(key, "")

    def getSettingBool(self, key):
        return str(self._settings.get(key, "false")).lower() == "true"

    def getAddonInfo(self, key):
        if key == "id":
            return self.addon_id
        if key == "profile":
            return "/tmp/mercadoplay_test_profile"
        if key == "name":
            return "MercadoLibre Play"
        if key == "version":
            return "1.4.1"
        return ""

    def setSetting(self, key, value):  # handy for tests
        self._settings[key] = str(value)
