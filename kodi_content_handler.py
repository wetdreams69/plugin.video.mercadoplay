import sys
import urllib.parse
import xbmcplugin
import xbmcgui
import xbmc

class KodiContentHandler:
    def __init__(self, addon_handle):
        self.addon_handle = addon_handle
        xbmcplugin.setContent(addon_handle, 'videos')

    def build_url(self, query):
        return sys.argv[0] + '?' + urllib.parse.urlencode(query)

    def add_directory_item(self, url, listitem, is_folder=True):
        xbmcplugin.addDirectoryItem(
            handle=self.addon_handle,
            url=url,
            listitem=listitem,
            isFolder=is_folder
        )

    def end_directory(self):
        xbmcplugin.endOfDirectory(self.addon_handle)

    def resolve_url(self, success, listitem):
        xbmcplugin.setResolvedUrl(self.addon_handle, success, listitem)

    def create_list_item(self, label="", path=""):
        return xbmcgui.ListItem(label=label, path=path)

    def show_notification(self, title, message, icon=xbmcgui.NOTIFICATION_INFO, time=3000):
        xbmcgui.Dialog().notification(title, message, icon, time)