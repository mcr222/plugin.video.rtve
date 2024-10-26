from builtins import str
from builtins import object

from resources.lib.utils.Utils import buildUrl
from resources.lib.rtve.rtve import rtve
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import time

class UI(object):

    def __init__(self, base_url, addon_handle, args):
        xbmc.log("plugin.video.rtve classe UI - start init() ")
        addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self.rtve = rtve(addon_path, addon)
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
            lFolder = self.rtve.listHome()

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("plugin.video.rtve - UI.run() Home - No existeixen elements")

        elif mode[0] == 'getProgrames':
            xbmc.log("plugin.video.rtve - Programes")
            (folders, videos) = self.rtve.listProgrames(url[0])
            self.listFolder(folders, False)
            self.listVideos(videos)

        elif mode[0] == 'playVideo':
            self.playVideo(url[0])

    def listVideos(self, lVideos):
        xbmc.log("plugin.video.rtve - UI - listVideos - Numero videos: " + str(len(lVideos)))

        for video in lVideos:
            # Create a list item with a text label
            list_item = xbmcgui.ListItem(label=video.title)
            # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
            # Here we use only poster for simplicity's sake.
            # In a real-life plugin you may need to set multiple image types.
            list_item.setArt({'poster': video.iconImage})
            list_item.setProperty('IsPlayable', 'true')
            # Set additional info for the list item via InfoTag.
            # 'mediatype' is needed for skin to display info for this ListItem correctly.
            info_tag = list_item.getVideoInfoTag()
            info_tag.setMediaType('movie')
            info_tag.setTitle(video.title)
            info_tag.setPlot(video.information)
            # Set 'IsPlayable' property to 'true'.

            url =  video.url
            # Add the list item to a virtual Kodi folder.
            # is_folder = False means that this item won't open any sub-list.
            is_folder = False
            # Add our item to the Kodi virtual folder listing.
            xbmc.log("plugin.video.rtve - UI - directory item " + str(url))
            urlPlugin = buildUrl({'mode': 'playVideo', 'url': url}, self.base_url)

            xbmcplugin.addDirectoryItem(self.addon_handle, urlPlugin, list_item, is_folder)
            # Add sort methods for the virtual folder items
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.addon_handle)

    def listFolder(self, lFolderVideos, enddirectory=True):
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

        if enddirectory:
            xbmcplugin.endOfDirectory(self.addon_handle)

    class DRMStreamPlayer(xbmc.Player):
        def __init__(self):
            super().__init__()
            self.is_playing = False
            self.playback_error = False

        def onPlayBackStarted(self):
            self.is_playing = True
            xbmc.log('Playback started successfully', xbmc.LOGINFO)

        def onPlayBackError(self):
            self.playback_error = True
            xbmc.log('Playback error occurred', xbmc.LOGERROR)

        def onPlayBackStopped(self):
            self.is_playing = False

    def playVideo(self,videoId):
        xbmc.log("plugin.video.rtve -UI - playVideo " + str(videoId))

        streamUrl = "https://ztnr.rtve.es/ztnr/{}.mpd".format(
            videoId)
        xbmc.log("plugin.video.rtve - UI - playVideo apijson url" + str(streamUrl))

        from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel
        from urllib.parse import quote

        # Constants
        PROTOCOL = 'mpd'
        DRM = 'com.widevine.alpha'

        # Stream configuration
        stream_url = "https://ztnr.rtve.es/ztnr/16302617.mpd"
        license_url = "https://3e6900a5.drm-widevine-licensing.axprod.net/AcquireLicense"
        drm_header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2ZXJzaW9uIjoxLCJjb21fa2V5X2lkIjoiOWRlYWZhMWUtN2UzNy00MzRhLWJkYWYtYWY1MDAxMGVlMTNhIiwibWVzc2FnZSI6eyJ0eXBlIjoiZW50aXRsZW1lbnRfbWVzc2FnZSIsInZlcnNpb24iOjIsImxpY2Vuc2UiOnsic3RhcnRfZGF0ZXRpbWUiOiIyMDI0LTEwLTI0VDE3OjA4OjIwLjM5MloiLCJleHBpcmF0aW9uX2RhdGV0aW1lIjoiMjAyNC0xMS0wMVQxODowODoyMC4zOTJaIiwiYWxsb3dfcGVyc2lzdGVuY2UiOnRydWV9LCJjb250ZW50X2tleXNfc291cmNlIjp7ImlubGluZSI6W3siaWQiOiI0NTRhNGYwOS0wMzI0LWMzOTgtN2RlZC1jZjkwMGFiZGZkNGUiLCJ1c2FnZV9wb2xpY3kiOiJQb2xpY3kgQSJ9XX0sImNvbnRlbnRfa2V5X3VzYWdlX3BvbGljaWVzIjpbeyJuYW1lIjoiUG9saWN5IEEiLCJmYWlycGxheSI6eyJoZGNwIjoiVFlQRTAifSwicGxheXJlYWR5Ijp7Im1pbl9kZXZpY2Vfc2VjdXJpdHlfbGV2ZWwiOjE1MCwicGxheV9lbmFibGVycyI6WyI3ODY2MjdEOC1DMkE2LTQ0QkUtOEY4OC0wOEFFMjU1QjAxQTciXX19XX0sImJlZ2luX2RhdGUiOiIyMDI0LTEwLTI0VDE3OjA4OjIwLjM5MloiLCJleHBpcmF0aW9uX2RhdGUiOiIyMDI0LTExLTAxVDE4OjA4OjIwLjM5MloifQ.1blUNC8unlAi-zjMMpU9u_Mu7Ns5lF9jnpY-rwK0a3s"

        # HTTP headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Referer': 'https://www.rtve.es/',
            'Origin': 'https://www.rtve.es',
            'Accept': '*/*'
        }

        # Convert headers to Kodi format
        headers_string = '&'.join([f'{k}={quote(v)}' for k, v in headers.items()])

        try:
            # Initialize custom player
            player = self.DRMStreamPlayer()

            # Create and configure the ListItem
            play_item = xbmcgui.ListItem(path=stream_url)

            # Set required properties for DRM playback
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            play_item.setProperty('inputstream.adaptive.license_type', DRM)
            play_item.setProperty('inputstream.adaptive.manifest_headers', headers_string)
            play_item.setProperty('inputstream.adaptive.stream_headers', headers_string)

            # Configure license key with proper formatting and increased timeout
            license_header = f'X-AxDrm-Message={quote(drm_header)}'
            license_key = f'{license_url}|{license_header}|R{{SSM}}|'
            play_item.setProperty('inputstream.adaptive.license_key', license_key)

            # Set additional properties
            play_item.setMimeType('application/dash+xml')
            play_item.setContentLookup(False)

            # Add properties to help with buffering
            play_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
            play_item.setProperty('inputstream.adaptive.stream_buffer_size', '131072')
            play_item.setProperty('inputstream.adaptive.initial_buffer_duration', '5')

            # Add these buffer settings
            play_item.setProperty('inputstream.adaptive.stream_buffer_size', '262144')  # Increased buffer
            play_item.setProperty('inputstream.adaptive.initial_buffer_duration', '10')  # Longer initial buffer
            play_item.setProperty('inputstream.adaptive.max_bandwidth', '4000000')  # Higher bandwidth cap
            play_item.setProperty('inputstream.adaptive.min_bandwidth', '1000000')  # Minimum bandwidth
            play_item.setProperty('inputstream.adaptive.ignore_dispatch', 'true')  # Helps with smooth playback

            # Start playback
            player.play(item=stream_url, listitem=play_item)

            # Wait for playback to actually start

            # Log success
            xbmc.log('DRM Stream playback initiated successfully', xbmc.LOGINFO)

        except Exception as e:
            xbmc.log(f'Error playing DRM stream: {str(e)}', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', 'Failed to play DRM stream', xbmcgui.NOTIFICATION_ERROR)
