"""
Authentication module for RTVE Play
Handles login and session management
"""
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import xbmc
import xbmcaddon
import xbmcvfs
import os
from typing import Optional, Dict


class RTVEAuth:
    """Handles RTVE Play authentication"""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.cookie_file = xbmcvfs.translatePath(
            os.path.join(self.addon.getAddonInfo('profile'), 'cookies.txt')
        )
        self.cookie_jar = http.cookiejar.MozillaCookieJar()
        self.session_cookies = {}
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
                req = urllib.request.Request(
                    login_page_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                with opener.open(req, timeout=15) as response:
                    login_page_content = response.read().decode('utf-8')
                    xbmc.log("plugin.video.rtve - Retrieved login page", xbmc.LOGDEBUG)
                    
                    # Extract CSRF token or other required fields from the login page
                    csrf_token = None
                    import re
                    csrf_match = re.search(r'name=["\']_token["\'] value=["\']([^"\']+)["\']', login_page_content)
                    if csrf_match:
                        csrf_token = csrf_match.group(1)
                        xbmc.log(f"plugin.video.rtve - Found CSRF token: {csrf_token[:10]}...", xbmc.LOGDEBUG)
                    
                    # Look for other form fields that might be required
                    form_action = None
                    action_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', login_page_content)
                    if action_match:
                        form_action = action_match.group(1)
                        if form_action.startswith('/'):
                            form_action = 'https://secure2.rtve.es' + form_action
                        xbmc.log(f"plugin.video.rtve - Found form action: {form_action}", xbmc.LOGDEBUG)
                    
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Error getting login page: {str(e)}", xbmc.LOGDEBUG)
                # Continue with fallback approach
            
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
                                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                                        'Content-Type': content_type,
                                        'Accept': 'application/json, text/html, */*',
                                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                        'Referer': 'https://secure2.rtve.es/usuarios/acceso/login/',
                                        'Origin': 'https://secure2.rtve.es',
                                        'DNT': '1',
                                        'Connection': 'keep-alive',
                                    }
                                    
                                    req = urllib.request.Request(login_url, data=data, headers=headers)
                                    
                                    # Perform login
                                    with opener.open(req, timeout=15) as response:
                                        response_text = response.read().decode('utf-8')
                                        
                                        xbmc.log(f"plugin.video.rtve - Login response status: {response.status}", xbmc.LOGDEBUG)
                                        
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

