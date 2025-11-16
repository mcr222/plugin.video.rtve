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
        Login to RTVE Play using the current authentication system
        
        Args:
            username: RTVE Play username/email
            password: RTVE Play password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            xbmc.log("plugin.video.rtve - Attempting RTVE Play login", xbmc.LOGDEBUG)
            
            # Create opener with cookie handler
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
            
            # Step 1: Visit the main login page to get initial cookies and CSRF tokens
            login_page_url = "https://secure2.rtve.es/usuarios/acceso/login/"
            
            try:
                login_page_content = self._make_request(login_page_url)
                if not login_page_content:
                    xbmc.log("plugin.video.rtve - Failed to retrieve login page", xbmc.LOGERROR)
                    return False
                
                xbmc.log("plugin.video.rtve - Retrieved login page", xbmc.LOGDEBUG)
                
                # Extract CSRF token or other required fields from the login page
                csrf_token = None
                form_action = None
                csrf_match = re.search(r'name=["\']_token["\'] value=["\']([^"\']+)["\']', login_page_content)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    xbmc.log(f"plugin.video.rtve - Found CSRF token: {csrf_token[:10]}...", xbmc.LOGDEBUG)
                
                # Look for form action regardless of CSRF token presence
                action_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', login_page_content)
                if action_match:
                    form_action = action_match.group(1)
                    if form_action.startswith('/'):
                        form_action = 'https://secure2.rtve.es' + form_action
                    xbmc.log(f"plugin.video.rtve - Found form action: {form_action}", xbmc.LOGDEBUG)
                        
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Error getting login page: {str(e)}", xbmc.LOGDEBUG)
                # Continue with fallback approach
                csrf_token = None
                form_action = None
            
            # Step 2: Try different login endpoints and methods
            login_endpoints = [
                form_action if form_action else "https://secure2.rtve.es/usuarios/acceso/login/",
                "https://secure2.rtve.es/usuarios/acceso/login/",
                "https://www.rtve.es/usuarios/acceso/login",
                "https://extapp.rtve.es/idp/login.html",
                "https://extra.rtve.es/idp/login.html",
                "https://api.rtve.es/api/login",
                "https://www.rtve.es/api/login"
            ]
            
            for login_url in login_endpoints:
                try:
                    xbmc.log(f"plugin.video.rtve - Trying login endpoint: {login_url}", xbmc.LOGDEBUG)
                    
                    # Prepare different login data formats
                    login_data_formats = []
                    
                    # Standard form data with CSRF token if available
                    base_data = {'username': username, 'password': password}
                    if csrf_token:
                        base_data['_token'] = csrf_token
                    login_data_formats.append(base_data)
                    
                    # Alternative field names
                    login_data_formats.extend([
                        {'email': username, 'password': password, '_token': csrf_token} if csrf_token else {'email': username, 'password': password},
                        {'user': username, 'pass': password, '_token': csrf_token} if csrf_token else {'user': username, 'pass': password},
                        {'login': username, 'password': password, '_token': csrf_token} if csrf_token else {'login': username, 'password': password},
                        {'usuario': username, 'clave': password, '_token': csrf_token} if csrf_token else {'usuario': username, 'clave': password},
                        # OAuth-style
                        {'username': username, 'password': password, 'grant_type': 'password'},
                        # JSON format
                        {'username': username, 'password': password, 'remember': True}
                    ])
                    
                    for login_data in login_data_formats:
                        try:
                            # Try both form-encoded and JSON requests
                            for content_type in ['application/x-www-form-urlencoded', 'application/json']:
                                try:
                                    if content_type == 'application/json':
                                        data = json.dumps(login_data).encode('utf-8')
                                    else:
                                        data = urllib.parse.urlencode(login_data).encode('utf-8')
                                    
                                    headers = {
                                        'Content-Type': content_type,
                                        'Accept': 'application/json, text/html, */*',
                                        'Referer': 'https://secure2.rtve.es/usuarios/acceso/login/',
                                        'Origin': 'https://secure2.rtve.es',
                                        'X-Requested-With': 'XMLHttpRequest' if content_type == 'application/json' else None
                                    }
                                    
                                    # Remove None values
                                    headers = {k: v for k, v in headers.items() if v is not None}
                                    
                                    # Perform login with robust request method
                                    response_text = self._make_request(login_url, data=data, headers=headers)
                                    
                                    if not response_text:
                                        xbmc.log(f"plugin.video.rtve - Login request failed with {content_type}", xbmc.LOGDEBUG)
                                        continue
                                        
                                    xbmc.log(f"plugin.video.rtve - Login response received with {content_type}", xbmc.LOGDEBUG)
                                    
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
                                        xbmc.log(f"plugin.video.rtve - JSON response: {response_data}", xbmc.LOGDEBUG)
                                        
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
                                    if (response.status in [200, 302] and has_success and not has_error) or response.status == 302:
                                        # Update session cookies
                                        for cookie in self.cookie_jar:
                                            self.session_cookies[cookie.name] = cookie.value
                                        
                                        self._save_cookies()
                                        xbmc.log("plugin.video.rtve - Login successful!", xbmc.LOGINFO)
                                        return True
                                    
                                    # If we got a redirect, follow it
                                    if response.status == 302:
                                        redirect_url = response.headers.get('Location')
                                        if redirect_url:
                                            xbmc.log(f"plugin.video.rtve - Following redirect to: {redirect_url}", xbmc.LOGDEBUG)
                                            # This might indicate successful login
                                            for cookie in self.cookie_jar:
                                                self.session_cookies[cookie.name] = cookie.value
                                            self._save_cookies()
                                            return True
                                        
                                except urllib.error.HTTPError as e:
                                    if e.code == 302:  # Redirect might indicate success
                                        for cookie in self.cookie_jar:
                                            self.session_cookies[cookie.name] = cookie.value
                                        self._save_cookies()
                                        xbmc.log("plugin.video.rtve - Login successful (redirect)", xbmc.LOGINFO)
                                        return True
                                    elif e.code not in [404, 405, 400]:  # Skip common errors
                                        xbmc.log(f"plugin.video.rtve - HTTP {e.code} for {login_url}", xbmc.LOGDEBUG)
                                    continue
                                except Exception as e:
                                    xbmc.log(f"plugin.video.rtve - Error with content type {content_type}: {str(e)}", xbmc.LOGDEBUG)
                                    continue
                                    
                        except Exception as e:
                            xbmc.log(f"plugin.video.rtve - Error trying login data format: {str(e)}", xbmc.LOGDEBUG)
                            continue
                            
                except Exception as e:
                    xbmc.log(f"plugin.video.rtve - Error with endpoint {login_url}: {str(e)}", xbmc.LOGDEBUG)
                    continue
            
            # Step 3: Fallback - try to get session cookies by visiting the main site
            xbmc.log("plugin.video.rtve - Trying fallback cookie approach", xbmc.LOGDEBUG)
            try:
                # Visit main RTVE Play page to establish session
                main_page_url = "https://www.rtve.es/play/"
                req = urllib.request.Request(
                    main_page_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                    }
                )
                opener.open(req, timeout=10)
                
                # Update session cookies from main page visit
                for cookie in self.cookie_jar:
                    self.session_cookies[cookie.name] = cookie.value
                self._save_cookies()
                
                xbmc.log("plugin.video.rtve - Fallback approach completed - cookies saved", xbmc.LOGDEBUG)
                # Return True to allow manual authentication via browser
                return True
                
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Fallback approach failed: {str(e)}", xbmc.LOGDEBUG)
            
            xbmc.log("plugin.video.rtve - All login attempts failed", xbmc.LOGERROR)
            return False
                    
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error during login: {str(e)}", xbmc.LOGERROR)
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

