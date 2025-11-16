from builtins import str
from builtins import object
from logging import DEBUG

from resources.lib.utils.Utils import buildUrl, getJsonData
from resources.lib.rtve.rtve import rtve
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import time

class UI(object):

    def __init__(self, base_url, addon_handle, args):
        xbmc.log("plugin.video.rtve classe UI - start init() ", xbmc.LOGDEBUG)
        self.addon = xbmcaddon.Addon()
        self.rtve = rtve(self.addon)
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
        
        elif mode[0] == 'login':
            self.handleLogin()
        
        elif mode[0] == 'logout':
            self.handleLogout()
        
        elif mode[0] == 'debug':
            self.handleDebug()

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

    def handleLogin(self):
        """Handle login action - prompt for credentials"""
        try:
            from resources.lib.utils.Auth import RTVEAuth
            
            # Prompt for username
            keyboard = xbmc.Keyboard('', 'Enter RTVE Play Username')
            keyboard.doModal()
            if not keyboard.isConfirmed():
                return
            username = keyboard.getText()
            
            if not username:
                xbmcgui.Dialog().ok('RTVE Login', 'Username is required.')
                return
            
            # Prompt for password
            keyboard = xbmc.Keyboard('', 'Enter RTVE Play Password', hidden=True)
            keyboard.doModal()
            if not keyboard.isConfirmed():
                return
            password = keyboard.getText()
            
            if not password:
                xbmcgui.Dialog().ok('RTVE Login', 'Password is required.')
                return
            
            xbmcgui.Dialog().notification('RTVE', 'Logging in...', xbmcgui.NOTIFICATION_INFO)
            auth = RTVEAuth()
            if auth.login(username, password):
                xbmcgui.Dialog().ok(
                    'RTVE Login',
                    'Login successful! You can now play videos.'
                )
            else:
                xbmcgui.Dialog().ok(
                    'RTVE Login',
                    'Login failed. Please check your username and password.'
                )
        except Exception as e:
            xbmc.log(f'Error during login: {str(e)}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok(
                'RTVE Login',
                f'Error: {str(e)}'
            )
    
    def handleLogout(self):
        """Handle logout action"""
        try:
            from resources.lib.utils.Auth import RTVEAuth
            auth = RTVEAuth()
            auth.logout()
            xbmcgui.Dialog().ok(
                'RTVE Logout',
                'Successfully logged out from RTVE Play.'
            )
        except Exception as e:
            xbmc.log(f'Error during logout: {str(e)}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok(
                'RTVE Logout',
                f'Error: {str(e)}'
            )
    
    def handleDebug(self):
        """Handle debug authentication action"""
        try:
            from resources.lib.utils.Auth import RTVEAuth
            auth = RTVEAuth()
            
            # Get debug information
            debug_info = auth.debug_auth_status()
            
            # Format debug information for display
            debug_text = "RTVE Authentication Debug Info:\n\n"
            debug_text += f"Logged in: {debug_info['logged_in']}\n"
            debug_text += f"Cookie count: {debug_info['cookie_count']}\n"
            debug_text += f"Cookie file exists: {debug_info['cookie_file_exists']}\n"
            debug_text += f"Cookie names: {debug_info['cookie_names']}\n"
            debug_text += f"RTVE connectivity: {debug_info['rtve_connectivity']}\n"
            debug_text += f"Token API connectivity: {debug_info['token_api_connectivity']}\n"
            
            # Show debug information
            xbmcgui.Dialog().textviewer('RTVE Debug Information', debug_text)
            
            # Ask if user wants to test DRM authentication with a specific video
            if xbmcgui.Dialog().yesno(
                'RTVE Debug',
                'Do you want to test DRM authentication with a specific video ID?'
            ):
                keyboard = xbmc.Keyboard('', 'Enter Video ID for DRM Test')
                keyboard.doModal()
                if keyboard.isConfirmed():
                    video_id = keyboard.getText()
                    if video_id:
                        # Test DRM authentication
                        test_results = auth.test_drm_authentication(video_id)
                        
                        # Format test results
                        test_text = f"DRM Authentication Test Results:\n\n"
                        test_text += f"Video ID: {test_results['video_id']}\n"
                        test_text += f"Auth status: {test_results['auth_status']}\n"
                        test_text += f"Token request: {test_results['token_request']}\n"
                        test_text += f"License URL: {test_results['license_url']}\n"
                        
                        if 'license_server' in test_results:
                            test_text += f"License server: {test_results['license_server']}\n"
                        
                        if 'test_error' in test_results:
                            test_text += f"Test error: {test_results['test_error']}\n"
                        
                        xbmcgui.Dialog().textviewer('DRM Test Results', test_text)
            
        except Exception as e:
            xbmc.log(f'Error during debug: {str(e)}', xbmc.LOGERROR)
            xbmcgui.Dialog().ok(
                'RTVE Debug',
                f'Error: {str(e)}'
            )

    def playVideo(self,videoId):
        xbmc.log("plugin.video.rtve -UI - playVideo " + str(videoId), xbmc.LOGDEBUG)

        stream_url = "https://ztnr.rtve.es/ztnr/{}.mpd".format(videoId)
        xbmc.log("plugin.video.rtve - UI - playVideo stream url: " + str(stream_url), xbmc.LOGDEBUG)

        license_url = ""
        auth_token = None
        
        # Get authentication instance
        auth = None
        try:
            from resources.lib.utils.Auth import RTVEAuth
            auth = RTVEAuth()
        except Exception as e:
            xbmc.log(f'Error initializing auth: {str(e)}', xbmc.LOGERROR)
        
        try:
            # Try to get token with authentication
            tokenUrl = "https://api.rtve.es/api/token/{}".format(videoId)
            xbmc.log(f"plugin.video.rtve - Requesting token from: {tokenUrl}", xbmc.LOGDEBUG)
            
            # Use authenticated request for token
            tokenJson = getJsonData(tokenUrl, max_retries=3, use_auth=True)
            xbmc.log("plugin.video.rtve - Token API response: " + str(tokenJson), xbmc.LOGDEBUG)

            # Extract license URL and other DRM info
            if 'widevineURL' in tokenJson:
                license_url = tokenJson['widevineURL']
                xbmc.log("plugin.video.rtve - Widevine license URL: " + str(license_url), xbmc.LOGDEBUG)
            else:
                xbmc.log("plugin.video.rtve - No widevineURL in token response", xbmc.LOGERROR)
                # Try alternative field names
                for field in ['licenseUrl', 'license_url', 'drm_license_url', 'drmLicenseUrl']:
                    if field in tokenJson:
                        license_url = tokenJson[field]
                        xbmc.log(f"plugin.video.rtve - Found license URL in field '{field}': {license_url}", xbmc.LOGDEBUG)
                        break
            
            # Extract authentication token if available
            for token_field in ['token', 'auth_token', 'access_token', 'bearer_token']:
                if token_field in tokenJson:
                    auth_token = tokenJson[token_field]
                    xbmc.log(f"plugin.video.rtve - Found auth token in field '{token_field}'", xbmc.LOGDEBUG)
                    break
                    
        except Exception as e:
            xbmc.log(f'Error getting DRM token: {str(e)}', xbmc.LOGERROR)
            
            # Check if it's an authentication error
            error_msg = str(e).lower()
            if '401' in error_msg or '403' in error_msg or 'unauthorized' in error_msg or 'forbidden' in error_msg:
                xbmcgui.Dialog().ok(
                    'RTVE Authentication Error',
                    'Authentication required. Please login first using the "Login to RTVE Play" option in the main menu.'
                )
                return
            elif '404' in error_msg:
                xbmcgui.Dialog().ok(
                    'RTVE Content Error',
                    'Content not found. This video may not be available or may have been removed.'
                )
                return
            elif 'network' in error_msg or 'timeout' in error_msg:
                xbmcgui.Dialog().ok(
                    'RTVE Network Error',
                    'Network error occurred. Please check your internet connection and try again.'
                )
                return
            else:
                # Try to continue without license URL for non-DRM content
                xbmc.log("plugin.video.rtve - Continuing without license URL - may be non-DRM content", xbmc.LOGDEBUG)
        
        # If no license URL was found, check if this might be non-DRM content
        if not license_url:
            xbmc.log("plugin.video.rtve - No license URL found, attempting to play as non-DRM content", xbmc.LOGDEBUG)
            # Try to play without DRM
            try:
                play_item = xbmcgui.ListItem(path=stream_url)
                play_item.setProperty('inputstream', 'inputstream.adaptive')
                play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                play_item.setMimeType('application/dash+xml')
                xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)
                return
            except Exception as e:
                xbmc.log(f'Error playing non-DRM stream: {str(e)}', xbmc.LOGERROR)
                xbmcgui.Dialog().ok(
                    'RTVE Playback Error',
                    'Unable to play this content. It may require authentication or may not be available.'
                )
                return


        from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel
        from urllib.parse import quote

        # Constants
        PROTOCOL = 'mpd'
        DRM = 'com.widevine.alpha'

        # Get authentication headers with enhanced error handling
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Referer': 'https://www.rtve.es/play/',
            'Origin': 'https://www.rtve.es',
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        # Add authentication headers if available
        if auth:
            try:
                auth_headers = auth.get_auth_headers()
                headers.update(auth_headers)
                xbmc.log("plugin.video.rtve - Added authentication headers to stream request", xbmc.LOGDEBUG)
            except Exception as e:
                xbmc.log(f'Error getting auth headers: {str(e)}', xbmc.LOGDEBUG)

        # Convert headers to Kodi format
        headers_string = '&'.join([f'{k}={quote(str(v))}' for k, v in headers.items()])
        
        # Build license key URL with proper authentication
        license_key_url = license_url
        
        # Add authentication token to license URL if available
        if auth_token and license_url:
            separator = '&' if '?' in license_url else '?'
            license_key_url = f"{license_url}{separator}token={auth_token}"
            xbmc.log(f"plugin.video.rtve - Added auth token to license URL", xbmc.LOGDEBUG)

        try:
            # Check if inputstream.adaptive is available
            is_helper = Helper(PROTOCOL, drm=DRM)
            if not is_helper.check_inputstream():
                xbmcgui.Dialog().ok(
                    'RTVE DRM Error',
                    'inputstream.adaptive is required for DRM playback but is not available.'
                )
                return

            # Initialize custom player
            player = self.DRMStreamPlayer()

            # Create and configure the ListItem
            play_item = xbmcgui.ListItem(path=stream_url)

            # Set required properties for DRM playback
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
            play_item.setProperty('inputstream.adaptive.manifest_headers', headers_string)
            play_item.setProperty('inputstream.adaptive.stream_headers', headers_string)

            # Configure license key with proper authentication
            if license_url:
                play_item.setProperty('inputstream.adaptive.license_type', DRM)
                play_item.setProperty('inputstream.adaptive.license_key', license_key_url)
                
                # Prepare license headers with authentication
                license_headers = headers.copy()
                
                # Add specific DRM-related headers
                license_headers.update({
                    'Content-Type': 'application/octet-stream',
                    'Accept': 'application/octet-stream, */*',
                })
                
                # Add authentication token as header if available
                if auth_token:
                    license_headers['Authorization'] = f'Bearer {auth_token}'
                    xbmc.log("plugin.video.rtve - Added Bearer token to license headers", xbmc.LOGDEBUG)
                
                # Convert license headers to Kodi format
                license_headers_string = '&'.join([f'{k}={quote(str(v))}' for k, v in license_headers.items()])
                play_item.setProperty('inputstream.adaptive.license_headers', license_headers_string)
                
                xbmc.log("plugin.video.rtve - Configured DRM license with authentication", xbmc.LOGDEBUG)
                
                # Additional DRM configuration
                play_item.setProperty('inputstream.adaptive.license_flags', 'persistent_storage')
                
                # Set server certificate if needed (some DRM systems require this)
                # This would need to be obtained from RTVE's DRM configuration
                # play_item.setProperty('inputstream.adaptive.server_certificate', server_cert)

            # Set additional properties
            play_item.setMimeType('application/dash+xml')
            play_item.setContentLookup(False)

            # Enhanced adaptive streaming configuration
            play_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
            
            # Improved buffering settings for DRM content
            play_item.setProperty('inputstream.adaptive.stream_buffer_size', '1048576')  # 1MB buffer
            play_item.setProperty('inputstream.adaptive.initial_buffer_duration', '20')  # 20 seconds
            play_item.setProperty('inputstream.adaptive.persistent_storage', 'true')
            play_item.setProperty('inputstream.adaptive.max_bandwidth', '20000000')  # 20 Mbps
            play_item.setProperty('inputstream.adaptive.min_bandwidth', '500000')   # 500 Kbps
            
            # Additional adaptive settings
            play_item.setProperty('inputstream.adaptive.chooser_bandwidth_max', '0')  # No limit
            play_item.setProperty('inputstream.adaptive.chooser_resolution_max', '1920x1080')
            play_item.setProperty('inputstream.adaptive.chooser_resolution_secure_max', '1920x1080')
            
            # DRM-specific settings
            if license_url:
                play_item.setProperty('inputstream.adaptive.license_data', '')  # Empty for standard Widevine
                play_item.setProperty('inputstream.adaptive.pre_init_data', '')
            
            # Log configuration for debugging
            xbmc.log(f"plugin.video.rtve - Stream URL: {stream_url}", xbmc.LOGDEBUG)
            xbmc.log(f"plugin.video.rtve - License URL: {license_key_url}", xbmc.LOGDEBUG)
            xbmc.log(f"plugin.video.rtve - Headers: {headers_string}", xbmc.LOGDEBUG)

            # Start playback
            xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=play_item)

            # Log success
            xbmc.log('plugin.video.rtve - DRM Stream playback initiated successfully', xbmc.LOGINFO)

        except Exception as e:
            xbmc.log(f'Error playing DRM stream: {str(e)}', xbmc.LOGERROR)
            
            # Provide specific error messages based on the error type
            error_msg = str(e).lower()
            if 'inputstream' in error_msg:
                xbmcgui.Dialog().ok(
                    'RTVE DRM Error',
                    'inputstream.adaptive addon is required for DRM playback. Please install it from the Kodi repository.'
                )
            elif 'widevine' in error_msg or 'drm' in error_msg:
                xbmcgui.Dialog().ok(
                    'RTVE DRM Error',
                    'DRM decryption failed. This may be due to authentication issues or unsupported DRM configuration.'
                )
            else:
                xbmcgui.Dialog().ok(
                    'RTVE Playback Error',
                    f'Failed to play DRM stream: {str(e)}'
                )
