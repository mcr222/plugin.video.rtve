from builtins import str
from builtins import object
from logging import DEBUG
import json
import urllib.request, urllib.parse, urllib.error

from resources.lib.utils.Utils import buildUrl, getJsonData
from resources.lib.rtve.rtve import rtve
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import time

# DRM and streaming constants
PROTOCOL_MPD = 'mpd'
PROTOCOL_HLS = 'hls'
DRM = 'com.widevine.alpha'

class UI(object):

    def __init__(self, base_url, addon_handle, args):
        xbmc.log("plugin.video.rtve classe UI - start init() ", xbmc.LOGDEBUG)
        addon = xbmcaddon.Addon()
        self.rtve = rtve(addon)
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.args = args
        self.mode = args.get('mode', None)
        self.url = args.get('url', [''])
        xbmc.log("plugin.video.rtve classe UI - finish init()", xbmc.LOGDEBUG)


    def run(self, mode, url):
        xbmc.log("plugin.video.rtve classe UI - run()  mode = " + str(mode) + ", url " + str(url), xbmc.LOGDEBUG)

        if mode == None:
            xbmc.log("plugin.video.rtve classe UI - mode = None", xbmc.LOGDEBUG)
            lFolder = self.rtve.listHome()

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("plugin.video.rtve - UI.run() Home - No existeixen elements", xbmc.LOGDEBUG)

        elif mode[0] == 'getProgrames':
            xbmc.log("plugin.video.rtve - Programes", xbmc.LOGDEBUG)
            (folders, videos) = self.rtve.listProgrames(url[0])
            self.listFolder(folders, False)
            self.listVideos(videos)

        elif mode[0] == 'playVideo':
            self.playVideo(url[0])

    def listVideos(self, lVideos):
        xbmc.log("plugin.video.rtve - UI - listVideos - Numero videos: " + str(len(lVideos)), xbmc.LOGDEBUG)

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
            xbmc.log("plugin.video.rtve - UI - directory item " + str(url), xbmc.LOGDEBUG)
            urlPlugin = buildUrl({'mode': 'playVideo', 'url': url}, self.base_url)

            xbmcplugin.addDirectoryItem(self.addon_handle, urlPlugin, list_item, is_folder)
            # Add sort methods for the virtual folder items
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.addon_handle)

    def listFolder(self, lFolderVideos, enddirectory=True):
        xbmc.log("plugin.video.rtve classe UI - listFolder", xbmc.LOGDEBUG)
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
            xbmc.log('Playback started successfully', xbmc.LOGDEBUG)

        def onPlayBackError(self):
            self.playback_error = True
            xbmc.log('Playback error occurred', xbmc.LOGERROR)

        def onPlayBackStopped(self):
            self.is_playing = False

    def playVideo(self, videoId):
        """Enhanced video playback with better device compatibility and error handling"""
        xbmc.log("plugin.video.rtve - UI - playVideo " + str(videoId), xbmc.LOGDEBUG)

        if str(videoId).lower().startswith("http"):
            xbmc.log("plugin.video.rtve - UI - is direct stream link", xbmc.LOGDEBUG)
            # For direct stream links
            if videoId.lower().endswith('.m3u8'):
                self.playHLSStream(videoId)
            elif videoId.lower().endswith('.mp4'):
                self.playMP4Stream(videoId)
            elif videoId.lower().endswith('.mpd'):
                self.playMPDStream(videoId)
            else:
                # Try to play directly as fallback
                xbmc.Player().play(videoId)
            return

        # For RTVE video IDs, try to get direct streaming URLs first
        direct_url = self.getRTVEDirectUrl(videoId)
        if direct_url:
            xbmc.log("plugin.video.rtve - UI - Found direct URL: " + direct_url, xbmc.LOGDEBUG)
            if direct_url.lower().endswith('.mp4'):
                self.playMP4Stream(direct_url)
            elif direct_url.lower().endswith('.m3u8'):
                self.playHLSStream(direct_url)
            else:
                # Try to play directly
                self.playMP4Stream(direct_url)
            return

        # Fallback to DRM MPD approach if direct URL not available
        xbmc.log("plugin.video.rtve - UI - No direct URL found, trying DRM approach", xbmc.LOGDEBUG)
        stream_url = "https://ztnr.rtve.es/ztnr/{}.mpd".format(videoId)
        xbmc.log("plugin.video.rtve - UI - MPD URL: " + str(stream_url), xbmc.LOGDEBUG)

        # Try to get license URL from RTVE API
        license_url = self.getRTVELicenseUrl(videoId)
        
        # Play the MPD stream with DRM
        self.playMPDStream(stream_url, license_url, needs_drm=True)

    def getRTVEDirectUrl(self, videoId):
        """Get direct streaming URL for RTVE content (preferred method)"""
        try:
            # Try the ztnr JSON endpoint first for direct MP4 URLs
            ztnr_url = "https://ztnr.rtve.es/ztnr/{}.json".format(videoId)
            xbmc.log("plugin.video.rtve - UI - Trying ztnr JSON: " + ztnr_url, xbmc.LOGDEBUG)
            
            ztnr_data = getJsonData(ztnr_url)
            xbmc.log("plugin.video.rtve - UI - ztnr response: " + str(ztnr_data), xbmc.LOGDEBUG)
            
            if isinstance(ztnr_data, list) and len(ztnr_data) > 0:
                video_info = ztnr_data[0]
                direct_link = video_info.get('link', '')
                if direct_link:
                    xbmc.log("plugin.video.rtve - UI - Found direct link: " + direct_link, xbmc.LOGDEBUG)
                    return direct_link
            
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error getting direct URL from ztnr: " + str(e), xbmc.LOGDEBUG)
        
        # Try alternative approaches if ztnr fails
        try:
            # Try to get video details and look for streaming URLs
            video_url = "https://api.rtve.es/api/videos/{}".format(videoId)
            video_data = getJsonData(video_url)
            
            if 'page' in video_data and 'items' in video_data['page'] and len(video_data['page']['items']) > 0:
                video_item = video_data['page']['items'][0]
                
                # Look for any streaming URLs in the video data
                def find_streaming_urls(obj):
                    urls = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, str) and any(ext in value.lower() for ext in ['.mp4', '.m3u8']):
                                urls.append(value)
                            elif isinstance(value, (dict, list)):
                                urls.extend(find_streaming_urls(value))
                    elif isinstance(obj, list):
                        for item in obj:
                            urls.extend(find_streaming_urls(item))
                    return urls
                
                streaming_urls = find_streaming_urls(video_item)
                if streaming_urls:
                    xbmc.log("plugin.video.rtve - UI - Found streaming URLs in video data: " + str(streaming_urls), xbmc.LOGDEBUG)
                    return streaming_urls[0]  # Return first found URL
                    
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error getting video details: " + str(e), xbmc.LOGDEBUG)
        
        return None

    def getRTVELicenseUrl(self, videoId):
        """Get the Widevine license URL for RTVE content"""
        try:
            tokenUrl = "https://api.rtve.es/api/token/{}".format(videoId)
            tokenJson = getJsonData(tokenUrl)
            xbmc.log("plugin.video.rtve - UI - token response: " + str(tokenJson), xbmc.LOGDEBUG)
            
            license_url = tokenJson.get('widevineURL', '')
            if license_url:
                xbmc.log("plugin.video.rtve - UI - license URL: " + str(license_url), xbmc.LOGDEBUG)
                return license_url
            else:
                xbmc.log("plugin.video.rtve - UI - No widevineURL in token response", xbmc.LOGWARNING)
                return None
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error getting license URL: " + str(e), xbmc.LOGERROR)
            return None

    def playMP4Stream(self, streamUrl):
        """Play a simple MP4 stream"""
        xbmc.log("plugin.video.rtve - UI - Playing MP4: " + streamUrl, xbmc.LOGDEBUG)
        try:
            play_item = xbmcgui.ListItem(path=streamUrl)
            play_item.setProperty('IsPlayable', 'true')
            xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error playing MP4: " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', 'Could not play MP4 video', xbmcgui.NOTIFICATION_ERROR)

    def playHLSStream(self, streamUrl):
        """Play an HLS stream using inputstream.adaptive"""
        xbmc.log("plugin.video.rtve - UI - Playing HLS: " + streamUrl, xbmc.LOGDEBUG)
        try:
            from inputstreamhelper import Helper
            is_helper = Helper(PROTOCOL_HLS)
            if is_helper.check_inputstream():
                play_item = xbmcgui.ListItem(path=streamUrl)
                play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL_HLS)
                play_item.setProperty('inputstream.adaptive.stream_headers',
                                    'User-Agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
                xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
            else:
                # Fallback to direct play if inputstream.adaptive is not available
                xbmc.log("plugin.video.rtve - UI - inputstream.adaptive not available for HLS, trying direct play", xbmc.LOGWARNING)
                play_item = xbmcgui.ListItem(path=streamUrl)
                xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
        except ImportError:
            # Fallback if inputstreamhelper is not available
            xbmc.log("plugin.video.rtve - UI - inputstreamhelper not available, trying direct play", xbmc.LOGWARNING)
            play_item = xbmcgui.ListItem(path=streamUrl)
            xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error playing HLS: " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', 'Could not play HLS video', xbmcgui.NOTIFICATION_ERROR)

    def playMPDStream(self, streamUrl, license_url=None, needs_drm=False):
        """Play an MPD (DASH) stream using inputstream.adaptive with optional DRM"""
        xbmc.log("plugin.video.rtve - UI - Playing MPD: " + streamUrl, xbmc.LOGDEBUG)
        
        try:
            from inputstreamhelper import Helper
            from urllib.parse import quote
            
            # Check if DRM is actually needed by examining the MPD manifest
            if not needs_drm:
                needs_drm = self.checkMPDForDRM(streamUrl)
            
            # Initialize inputstream helper with or without DRM
            if needs_drm:
                is_helper = Helper(PROTOCOL_MPD, drm=DRM)
            else:
                is_helper = Helper(PROTOCOL_MPD)
                
            if is_helper.check_inputstream():
                # HTTP headers for RTVE
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                    'Referer': 'https://www.rtve.es/',
                    'Origin': 'https://www.rtve.es',
                    'Accept': '*/*'
                }
                
                # Convert headers to Kodi format
                headers_string = '&'.join([f'{k}={quote(v)}' for k, v in headers.items()])
                
                # Create and configure the ListItem
                play_item = xbmcgui.ListItem(path=streamUrl)
                play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL_MPD)
                play_item.setProperty('inputstream.adaptive.manifest_headers', headers_string)
                play_item.setProperty('inputstream.adaptive.stream_headers', headers_string)
                
                # Set additional properties for better compatibility
                play_item.setMimeType('application/dash+xml')
                play_item.setContentLookup(False)
                play_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
                
                # Buffering settings for better performance
                play_item.setProperty('inputstream.adaptive.stream_buffer_size', '524288')
                play_item.setProperty('inputstream.adaptive.initial_buffer_duration', '15')
                play_item.setProperty('inputstream.adaptive.persistent_storage', 'true')
                play_item.setProperty('inputstream.adaptive.max_bandwidth', '20000000')
                play_item.setProperty('inputstream.adaptive.min_bandwidth', '500000')
                
                # Only set DRM properties if needed and license URL is available
                if needs_drm and license_url:
                    play_item.setProperty('inputstream.adaptive.license_type', DRM)
                    play_item.setProperty('inputstream.adaptive.license_key', license_url)
                    xbmc.log("plugin.video.rtve - UI - Using DRM with license: " + license_url, xbmc.LOGDEBUG)
                elif needs_drm and not license_url:
                    xbmc.log("plugin.video.rtve - UI - DRM needed but no license URL available", xbmc.LOGWARNING)
                    xbmcgui.Dialog().notification('Warning', 'DRM content but no license available', xbmcgui.NOTIFICATION_WARNING)
                
                # Start playback
                xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
                xbmc.log('plugin.video.rtve - UI - MPD playback initiated successfully', xbmc.LOGDEBUG)
                
            else:
                # Fallback to direct play if inputstream.adaptive is not available
                xbmc.log("plugin.video.rtve - UI - inputstream.adaptive not available, trying direct play", xbmc.LOGWARNING)
                play_item = xbmcgui.ListItem(path=streamUrl)
                xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
                
        except ImportError:
            # Fallback if inputstreamhelper is not available
            xbmc.log("plugin.video.rtve - UI - inputstreamhelper not available, trying direct play", xbmc.LOGWARNING)
            play_item = xbmcgui.ListItem(path=streamUrl)
            xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Error playing MPD: " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Error', 'Could not play video: ' + str(e), xbmcgui.NOTIFICATION_ERROR)

    def checkMPDForDRM(self, streamUrl):
        """Check if an MPD manifest contains DRM protection"""
        try:
            with urllib.request.urlopen(streamUrl, timeout=5) as response:
                mpd_content = response.read().decode('utf-8')
                if 'ContentProtection' in mpd_content:
                    xbmc.log("plugin.video.rtve - UI - DRM content protection detected in MPD", xbmc.LOGDEBUG)
                    return True
        except Exception as e:
            xbmc.log("plugin.video.rtve - UI - Could not check MPD for DRM: " + str(e), xbmc.LOGDEBUG)
        return False
