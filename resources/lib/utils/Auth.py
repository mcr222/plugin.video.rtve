"""
Authentication module for RTVE Play
Handles login and session management
"""
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import time
import random
import re
import xbmc
import xbmcaddon
import xbmcvfs
import os
from typing import Optional, Dict, List


class RTVEAuth:
    """Handles RTVE Play authentication"""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.cookie_file = xbmcvfs.translatePath(
            os.path.join(self.addon.getAddonInfo('profile'), 'cookies.txt')
        )
        self.cookie_jar = http.cookiejar.MozillaCookieJar()
        self.session_cookies = {}
        
        # Request configuration for better timeout handling
        try:
            from resources.lib.utils.NetworkConfig import network_config
            self.default_timeout = network_config.get_timeout()
            self.max_retries = network_config.get_max_retries()
            self.retry_delay = network_config.get_retry_delay()
            network_config.log_network_settings()
        except ImportError:
            # Fallback values if NetworkConfig is not available
            self.default_timeout = 30
            self.max_retries = 3
            self.retry_delay = 2
        
        self._load_cookies()
    
    def _load_cookies(self):
        """Load cookies from file if exists"""
        try:
            if xbmcvfs.exists(self.cookie_file):
                self.cookie_jar.load(self.cookie_file, ignore_discard=True, ignore_expires=True)
                # Extract cookies into a dict for easy access
                for cookie in self.cookie_jar:
                    self.session_cookies[cookie.name] = cookie.value
                xbmc.log(f"plugin.video.rtve - Loaded {len(self.session_cookies)} cookies", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error loading cookies: {str(e)}", xbmc.LOGERROR)
    
    def _save_cookies(self):
        """Save cookies to file"""
        try:
            # Ensure profile directory exists
            profile_dir = os.path.dirname(self.cookie_file)
            if not xbmcvfs.exists(profile_dir):
                xbmcvfs.mkdirs(profile_dir)
            
            # Save cookies
            self.cookie_jar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)
            xbmc.log("plugin.video.rtve - Cookies saved", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error saving cookies: {str(e)}", xbmc.LOGERROR)
    
    def _make_request(self, url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None, 
                     timeout: Optional[int] = None, max_retries: Optional[int] = None) -> Optional[str]:
        """
        Make HTTP request with retry logic and better timeout handling
        
        Args:
            url: URL to request
            data: POST data (if any)
            headers: Request headers
            timeout: Request timeout (uses default if None)
            max_retries: Maximum retry attempts (uses default if None)
            
        Returns:
            Response content as string, or None if failed
        """
        if timeout is None:
            timeout = self.default_timeout
        if max_retries is None:
            max_retries = self.max_retries
        if headers is None:
            headers = {}
        
        # Default headers for better compatibility
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Merge headers
        request_headers = {**default_headers, **headers}
        
        # Create opener with cookie support
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        
        for attempt in range(max_retries + 1):
            try:
                xbmc.log(f"plugin.video.rtve - Making request to {url} (attempt {attempt + 1}/{max_retries + 1})", xbmc.LOGDEBUG)
                
                # Create request
                req = urllib.request.Request(url, data=data, headers=request_headers)
                
                # Make request with timeout
                with opener.open(req, timeout=timeout) as response:
                    content = response.read()
                    
                    # Handle gzip/deflate encoding
                    if response.info().get('Content-Encoding') == 'gzip':
                        import gzip
                        content = gzip.decompress(content)
                    elif response.info().get('Content-Encoding') == 'deflate':
                        import zlib
                        content = zlib.decompress(content)
                    
                    # Update session cookies
                    for cookie in self.cookie_jar:
                        self.session_cookies[cookie.name] = cookie.value
                    
                    result = content.decode('utf-8', errors='ignore')
                    xbmc.log(f"plugin.video.rtve - Request successful (status: {response.status})", xbmc.LOGDEBUG)
                    return result
                    
            except urllib.error.HTTPError as e:
                xbmc.log(f"plugin.video.rtve - HTTP error {e.code}: {e.reason}", xbmc.LOGWARNING)
                if e.code in [401, 403, 404]:  # Don't retry for these errors
                    return None
                    
            except urllib.error.URLError as e:
                if "timed out" in str(e).lower():
                    xbmc.log(f"plugin.video.rtve - Request timed out (attempt {attempt + 1}): {str(e)}", xbmc.LOGWARNING)
                else:
                    xbmc.log(f"plugin.video.rtve - URL error (attempt {attempt + 1}): {str(e)}", xbmc.LOGWARNING)
                    
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Request error (attempt {attempt + 1}): {str(e)}", xbmc.LOGWARNING)
            
            # Wait before retry (exponential backoff with jitter)
            if attempt < max_retries:
                delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                xbmc.log(f"plugin.video.rtve - Waiting {delay:.1f}s before retry...", xbmc.LOGDEBUG)
                time.sleep(delay)
        
        xbmc.log(f"plugin.video.rtve - Request failed after {max_retries + 1} attempts", xbmc.LOGERROR)
        return None
    
    def login(self, username: str, password: str) -> bool:
        """
        Login to RTVE Play using Gigya authentication system
        
        Args:
            username: RTVE Play username/email
            password: RTVE Play password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            xbmc.log("plugin.video.rtve - Attempting RTVE Play login via Gigya", xbmc.LOGDEBUG)
            
            # Step 1: Get Gigya API key from login page
            login_page_url = "https://secure2.rtve.es/usuarios/acceso/login/"
            gigya_api_key = None
            
            try:
                login_page_content = self._make_request(login_page_url, timeout=10)
                if not login_page_content:
                    xbmc.log("plugin.video.rtve - Failed to retrieve login page", xbmc.LOGERROR)
                    return False
                
                xbmc.log("plugin.video.rtve - Retrieved login page", xbmc.LOGDEBUG)
                
                # Extract Gigya API key (handle HTML entities)
                import html
                gigya_match = re.search(r'gigyaApikey&quot;:&quot;([^&]+)&quot;', login_page_content)
                if not gigya_match:
                    # Try alternative patterns
                    gigya_match = re.search(r'gigyaApikey["\']:\s*["\']([^"\']+)["\']', login_page_content)
                
                if gigya_match:
                    gigya_api_key = html.unescape(gigya_match.group(1))
                    xbmc.log(f"plugin.video.rtve - Found Gigya API key: {gigya_api_key[:10]}...", xbmc.LOGDEBUG)
                else:
                    xbmc.log("plugin.video.rtve - Could not find Gigya API key", xbmc.LOGWARNING)
                    return False
                        
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Error getting login page: {str(e)}", xbmc.LOGERROR)
                return False
            
            # Step 2: Authenticate with Gigya
            if gigya_api_key:
                return self._gigya_login(gigya_api_key, username, password)
            else:
                xbmc.log("plugin.video.rtve - No Gigya API key found, trying fallback methods", xbmc.LOGWARNING)
                return self._fallback_login(username, password)
                
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def _gigya_login(self, api_key: str, username: str, password: str) -> bool:
        """
        Perform Gigya authentication
        
        Args:
            api_key: Gigya API key
            username: Username/email
            password: Password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Gigya login endpoint
            gigya_login_url = "https://accounts.gigya.com/accounts.login"
            
            # Prepare login data for Gigya
            login_data = {
                'apiKey': api_key,
                'loginID': username,
                'password': password,
                'format': 'json',
                'httpStatusCodes': 'false'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'Referer': 'https://secure2.rtve.es/usuarios/acceso/login/',
                'Origin': 'https://secure2.rtve.es'
            }
            
            data = urllib.parse.urlencode(login_data).encode('utf-8')
            
            xbmc.log("plugin.video.rtve - Attempting Gigya authentication", xbmc.LOGDEBUG)
            response_text = self._make_request(gigya_login_url, data=data, headers=headers, timeout=15)
            
            if not response_text:
                xbmc.log("plugin.video.rtve - Gigya login request failed", xbmc.LOGERROR)
                return False
            
            # Parse Gigya response
            try:
                response_data = json.loads(response_text)
                xbmc.log(f"plugin.video.rtve - Gigya response status: {response_data.get('errorCode', 'unknown')}", xbmc.LOGDEBUG)
                
                if response_data.get('errorCode') == 0:
                    # Successful login
                    session_token = response_data.get('sessionInfo', {}).get('sessionToken')
                    if session_token:
                        xbmc.log("plugin.video.rtve - Gigya login successful", xbmc.LOGDEBUG)
                        # Store session token for future use
                        self.session_cookies['gigya_session'] = session_token
                        self._save_cookies()
                        return True
                    else:
                        xbmc.log("plugin.video.rtve - No session token in Gigya response", xbmc.LOGWARNING)
                        return False
                else:
                    error_msg = response_data.get('errorMessage', 'Unknown error')
                    xbmc.log(f"plugin.video.rtve - Gigya login failed: {error_msg}", xbmc.LOGERROR)
                    return False
                    
            except json.JSONDecodeError:
                xbmc.log("plugin.video.rtve - Invalid JSON response from Gigya", xbmc.LOGERROR)
                return False
                
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Gigya login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def _fallback_login(self, username: str, password: str) -> bool:
        """
        Fallback login method for when Gigya is not available
        
        Args:
            username: Username/email
            password: Password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            xbmc.log("plugin.video.rtve - Trying fallback login methods", xbmc.LOGDEBUG)
            
            # Try a few key endpoints with reduced timeout
            login_endpoints = [
                "https://secure2.rtve.es/usuarios/acceso/login/",
                "https://www.rtve.es/api/login"
            ]
            
            for login_url in login_endpoints:
                try:
                    xbmc.log(f"plugin.video.rtve - Trying fallback endpoint: {login_url}", xbmc.LOGDEBUG)
                    
                    # Try only the most common data formats
                    login_data_formats = [
                        {'username': username, 'password': password},
                        {'email': username, 'password': password}
                    ]
                    
                    for login_data in login_data_formats:
                        try:
                            data = urllib.parse.urlencode(login_data).encode('utf-8')
                            headers = {
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Accept': 'application/json, text/html, */*',
                                'Referer': 'https://secure2.rtve.es/usuarios/acceso/login/',
                                'Origin': 'https://secure2.rtve.es'
                            }
                            
                            # Use shorter timeout for fallback
                            response_text = self._make_request(login_url, data=data, headers=headers, timeout=10, max_retries=1)
                            
                            if not response_text:
                                continue
                                
                            # Check for successful login indicators
                            success_indicators = [
                                'dashboard', 'perfil', 'cuenta', 'logout', 'cerrar sesion',
                                'access_token', 'token', 'success', 'usuario', 'bienvenido',
                                'welcome', 'profile', 'account'
                            ]
                            
                            # Check for error indicators
                            error_indicators = [
                                'error', 'incorrecto', 'invalid', 'failed', 'denied',
                                'usuario no encontrado', 'contraseña incorrecta'
                            ]
                            
                            response_lower = response_text.lower()
                            has_success = any(indicator in response_lower for indicator in success_indicators)
                            has_error = any(indicator in response_lower for indicator in error_indicators)
                            
                            # Try to parse as JSON for structured response
                            try:
                                response_data = json.loads(response_text)
                                xbmc.log(f"plugin.video.rtve - JSON response received", xbmc.LOGDEBUG)
                                
                                # Check JSON response for success
                                if (response_data.get('success') or 
                                    response_data.get('token') or 
                                    response_data.get('access_token') or
                                    response_data.get('user')):
                                    has_success = True
                                elif (response_data.get('error') or 
                                      response_data.get('message', '').lower().find('error') != -1):
                                    has_error = True
                            except:
                                pass
                            
                            # Check if login was successful
                            if has_success and not has_error:
                                # Update session cookies
                                for cookie in self.cookie_jar:
                                    self.session_cookies[cookie.name] = cookie.value
                                
                                self._save_cookies()
                                xbmc.log("plugin.video.rtve - Fallback login successful!", xbmc.LOGINFO)
                                return True
                                
                        except Exception as e:
                            xbmc.log(f"plugin.video.rtve - Error with fallback login: {str(e)}", xbmc.LOGDEBUG)
                            continue
                            
                except Exception as e:
                    xbmc.log(f"plugin.video.rtve - Error with fallback endpoint {login_url}: {str(e)}", xbmc.LOGDEBUG)
                    continue
            
            xbmc.log("plugin.video.rtve - All fallback login methods failed", xbmc.LOGWARNING)
            return False
            
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Fallback login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers including cookies
        
        Returns:
            Dictionary of headers with authentication
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Referer': 'https://www.rtve.es/play/',
            'Origin': 'https://www.rtve.es',
            'Accept': '*/*'
        }
        
        # Add cookies if available
        if self.session_cookies:
            cookie_string = '; '.join([f'{k}={v}' for k, v in self.session_cookies.items()])
            headers['Cookie'] = cookie_string
        
        return headers
    
    def get_cookie_string(self) -> str:
        """
        Get cookie string for requests
        
        Returns:
            Cookie string or empty string
        """
        if self.session_cookies:
            return '; '.join([f'{k}={v}' for k, v in self.session_cookies.items()])
        return ''
    
    def is_logged_in(self) -> bool:
        """
        Check if user is logged in
        
        Returns:
            True if cookies exist, False otherwise
        """
        # Check if we have session cookies
        if self.session_cookies:
            xbmc.log(f"plugin.video.rtve - Checking login status with {len(self.session_cookies)} cookies", xbmc.LOGDEBUG)
            
            # Log cookie names for debugging (without values for security)
            cookie_names = list(self.session_cookies.keys())
            xbmc.log(f"plugin.video.rtve - Available cookies: {cookie_names}", xbmc.LOGDEBUG)
            
            # Check for common session cookie names
            session_keys = ['JSESSIONID', 'sessionid', 'rtve_session', 'access_token', 'rtve_token', 
                          'auth_token', 'user_token', 'login_token', 'session_token', 'PHPSESSID',
                          'laravel_session', 'rtve_auth', 'rtve_user']
            
            found_session = any(key.lower() in [k.lower() for k in self.session_cookies.keys()] for key in session_keys)
            
            if found_session:
                xbmc.log("plugin.video.rtve - Found session cookies - user appears to be logged in", xbmc.LOGDEBUG)
            else:
                xbmc.log("plugin.video.rtve - No session cookies found - user may not be logged in", xbmc.LOGDEBUG)
            
            return found_session
        
        xbmc.log("plugin.video.rtve - No cookies available - user is not logged in", xbmc.LOGDEBUG)
        return False
    
    def logout(self):
        """Clear authentication cookies"""
        self.session_cookies = {}
        self.cookie_jar = http.cookiejar.MozillaCookieJar()
        try:
            if xbmcvfs.exists(self.cookie_file):
                xbmcvfs.delete(self.cookie_file)
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error deleting cookie file: {str(e)}", xbmc.LOGERROR)
        xbmc.log("plugin.video.rtve - Logged out", xbmc.LOGDEBUG)
    
    def debug_auth_status(self) -> Dict[str, str]:
        """
        Get detailed authentication status for debugging
        
        Returns:
            Dictionary with authentication debug information
        """
        debug_info = {
            'logged_in': str(self.is_logged_in()),
            'cookie_count': str(len(self.session_cookies)),
            'cookie_file_exists': str(xbmcvfs.exists(self.cookie_file)),
            'cookie_names': ', '.join(self.session_cookies.keys()) if self.session_cookies else 'None'
        }
        
        # Test connectivity to RTVE
        try:
            import urllib.request
            req = urllib.request.Request('https://www.rtve.es/play/', headers=self.get_auth_headers())
            with urllib.request.urlopen(req, timeout=5) as response:
                debug_info['rtve_connectivity'] = f'OK ({response.status})'
        except Exception as e:
            debug_info['rtve_connectivity'] = f'Error: {str(e)}'
        
        # Test token API connectivity
        try:
            req = urllib.request.Request('https://api.rtve.es/api/token/test', headers=self.get_auth_headers())
            with urllib.request.urlopen(req, timeout=5) as response:
                debug_info['token_api_connectivity'] = f'Response ({response.status})'
        except Exception as e:
            debug_info['token_api_connectivity'] = f'Error: {str(e)}'
        
        return debug_info
    
    def test_drm_authentication(self, video_id: str) -> Dict[str, str]:
        """
        Test DRM authentication for a specific video
        
        Args:
            video_id: Video ID to test
            
        Returns:
            Dictionary with test results
        """
        test_results = {
            'video_id': video_id,
            'auth_status': 'Unknown',
            'token_request': 'Not attempted',
            'license_url': 'Not found'
        }
        
        try:
            # Test authentication status
            test_results['auth_status'] = 'Logged in' if self.is_logged_in() else 'Not logged in'
            
            # Test token request
            from resources.lib.utils.Utils import getJsonData
            token_url = f"https://api.rtve.es/api/token/{video_id}"
            
            try:
                token_data = getJsonData(token_url, max_retries=1, use_auth=True)
                test_results['token_request'] = 'Success'
                
                if 'widevineURL' in token_data:
                    test_results['license_url'] = 'Found'
                    # Test license server connectivity (without actually requesting a license)
                    license_url = token_data['widevineURL']
                    try:
                        import urllib.request
                        req = urllib.request.Request(license_url, headers=self.get_auth_headers())
                        req.get_method = lambda: 'HEAD'  # HEAD request to test connectivity
                        with urllib.request.urlopen(req, timeout=5) as response:
                            test_results['license_server'] = f'Accessible ({response.status})'
                    except Exception as e:
                        test_results['license_server'] = f'Error: {str(e)}'
                else:
                    test_results['license_url'] = 'Not found in response'
                    
            except Exception as e:
                test_results['token_request'] = f'Failed: {str(e)}'
                
        except Exception as e:
            test_results['test_error'] = str(e)
        
        return test_results

