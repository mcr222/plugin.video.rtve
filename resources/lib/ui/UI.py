import json
from builtins import str
from builtins import object

import urllib.request, urllib.parse, urllib.error

from resources.lib.utils.Utils import buildUrl
from resources.lib.rtve.rtve import rtve
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import urllib.parse

PROTOCOL = 'mpd'
DRM = 'com.widevine.alpha'
LICENSE_URL = 'https://cwip-shaka-proxy.appspot.com/no_auth'


class UI(object):

    def __init__(self, base_url, addon_handle, args):
        xbmc.log("plugin.video.rtve classe UI - start init() ")
        addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self.tv3 = rtve(addon_path, addon)
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.args = args
        self.mode = args.get('mode', None)
        self.url = args.get('url', [''])
        xbmc.log("plugin.video.rtve classe UI - finish init()")


    def run(self, mode, url):
        xbmc.log("plugin.video.rtve classe UI - run()  mode = " + str(mode) + ", url " + str(url))

        if mode == None:
            xbmc.log("plugin.video.rtve classe UI - mode = None")
            lFolder = self.tv3.listHome()

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("plugin.video.rtve - UI.run() Home - No existeixen elements")

        elif mode[0] == 'getProgrames':
            xbmc.log("plugin.video.rtve - Programes")
            lFolder = self.tv3.listProgrames(url[0])
            self.listFolder(lFolder)

        elif mode[0] == 'playVideo':
            self.playVideo(url[0])

    def listFolder(self, lFolderVideos):
        xbmc.log("plugin.video.rtve classe UI - listFolder")
        for folder in lFolderVideos:

            mode = folder.mode
            name = folder.name
            url = folder.url
            iconImage = folder.iconImage
            thumbImage = folder.thumbnailImage

            urlPlugin = buildUrl({'mode': mode, 'url': url}, self.base_url)
            liz = xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"title": name})
            liz.setArt({'thumb': thumbImage, 'icon' : iconImage})

            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=urlPlugin, listitem=liz, isFolder=True)
        xbmcplugin.endOfDirectory(self.addon_handle)

    def playVideo(self,videoId):
        xbmc.log("plugin.video.rtve -UI - playVideo " + str(videoId))

        streamUrl = "http://ztnr.rtve.es/ztnr/{}.mpd".format(
            videoId)
        xbmc.log("plugin.video.rtve - UI - playVideo apijson url" + str(streamUrl))

        from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel

        is_helper = Helper(PROTOCOL, drm=DRM)
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=streamUrl)
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.stream_headers',
                                  'User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            play_item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')
            play_item.setProperty('inputstream.adaptive.manifest_update_interval', '10')
            play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            play_item.setProperty('inputstream.adaptive.license_type', DRM)
            play_item.setProperty('inputstream.adaptive.license_key', LICENSE_URL + '||R{SSM}|')
            xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)