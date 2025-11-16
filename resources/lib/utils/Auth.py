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
            login_page_url = "https://www.rtve.es/usuarios/acceso/login/"
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
            
            # Step 2: Try direct RTVE authentication first (more reliable)
            xbmc.log("plugin.video.rtve - Attempting direct RTVE authentication", xbmc.LOGDEBUG)
            if self._direct_rtve_login(username, password):
                return True
            
            # Step 3: Fallback to Gigya if direct login fails
            if gigya_api_key:
                xbmc.log("plugin.video.rtve - Direct RTVE login failed, trying Gigya as fallback", xbmc.LOGDEBUG)
                # Try using stored data center first if available
                stored_data_center = self.session_cookies.get('gigya_data_center')
                if stored_data_center:
                    xbmc.log(f"plugin.video.rtve - Using previously successful data center: {stored_data_center}", xbmc.LOGDEBUG)
                    if self._gigya_login_single_datacenter(gigya_api_key, username, password, stored_data_center):
                        return True
                    else:
                        xbmc.log("plugin.video.rtve - Stored data center failed, trying all data centers", xbmc.LOGDEBUG)
                
                return self._gigya_login(gigya_api_key, username, password)
            else:
                xbmc.log("plugin.video.rtve - No Gigya API key found and direct login failed", xbmc.LOGERROR)
                return False
                
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def _gigya_login_single_datacenter(self, api_key: str, username: str, password: str, data_center: str) -> bool:
        """
        Perform Gigya authentication using a specific data center
        
        Args:
            api_key: Gigya API key
            username: Username/email
            password: Password
            data_center: Specific data center to use (e.g., 'eu1.gigya.com')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            gigya_login_url = f"https://accounts.{data_center}/accounts.login"
            
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
                'Referer': 'https://www.rtve.es/usuarios/acceso/login/',
                'Origin': 'https://www.rtve.es'
            }
            
            data = urllib.parse.urlencode(login_data).encode('utf-8')
            
            response_text = self._make_request(gigya_login_url, data=data, headers=headers, timeout=15)
            
            if not response_text:
                return False
            
            # Parse Gigya response
            try:
                response_data = json.loads(response_text)
                error_code = response_data.get('errorCode', 'unknown')
                
                if error_code == 0:
                    # Successful login
                    session_token = response_data.get('sessionInfo', {}).get('sessionToken')
                    if session_token:
                        xbmc.log(f"plugin.video.rtve - Gigya login successful using stored data center: {data_center}", xbmc.LOGINFO)
                        # Store session token
                        self.session_cookies['gigya_session'] = session_token
                        self._save_cookies()
                        return True
                
                return False
                    
            except json.JSONDecodeError:
                return False
                
        except Exception:
            return False
    
    def _gigya_login(self, api_key: str, username: str, password: str) -> bool:
        """
        Perform Gigya authentication with automatic data center detection
        
        Args:
            api_key: Gigya API key
            username: Username/email
            password: Password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Gigya data centers to try (EU first for RTVE, then US, then AU)
            data_centers = [
                'eu1.gigya.com',  # European data center (most likely for RTVE)
                'us1.gigya.com',  # US data center
                'au1.gigya.com'   # Australian data center
            ]
            
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
                'Referer': 'https://www.rtve.es/usuarios/acceso/login/',
                'Origin': 'https://www.rtve.es'
            }
            
            data = urllib.parse.urlencode(login_data).encode('utf-8')
            
            xbmc.log("plugin.video.rtve - Attempting Gigya authentication with data center detection", xbmc.LOGDEBUG)
            
            # Try each data center until we find the correct one
            for data_center in data_centers:
                gigya_login_url = f"https://accounts.{data_center}/accounts.login"
                xbmc.log(f"plugin.video.rtve - Trying Gigya data center: {data_center}", xbmc.LOGDEBUG)
                
                response_text = self._make_request(gigya_login_url, data=data, headers=headers, timeout=15)
                
                if not response_text:
                    xbmc.log(f"plugin.video.rtve - No response from {data_center}, trying next data center", xbmc.LOGDEBUG)
                    continue
                
                # Parse Gigya response
                try:
                    response_data = json.loads(response_text)
                    error_code = response_data.get('errorCode', 'unknown')
                    xbmc.log(f"plugin.video.rtve - Gigya response from {data_center} - status: {error_code}", xbmc.LOGDEBUG)
                    
                    # Check if this is the wrong data center
                    if error_code == 301001:
                        xbmc.log(f"plugin.video.rtve - Data center {data_center} is invalid for this API key, trying next", xbmc.LOGDEBUG)
                        continue
                    
                    if error_code == 0:
                        # Successful login
                        session_token = response_data.get('sessionInfo', {}).get('sessionToken')
                        if session_token:
                            xbmc.log(f"plugin.video.rtve - Gigya login successful using data center: {data_center}", xbmc.LOGINFO)
                            # Store session token and data center for future use
                            self.session_cookies['gigya_session'] = session_token
                            self.session_cookies['gigya_data_center'] = data_center
                            self._save_cookies()
                            return True
                        else:
                            xbmc.log(f"plugin.video.rtve - No session token in response from {data_center}", xbmc.LOGWARNING)
                            continue
                    else:
                        # Other error - could be credentials issue, log and try next data center
                        error_msg = response_data.get('errorMessage', 'Unknown error')
                        xbmc.log(f"plugin.video.rtve - Gigya error from {data_center}: {error_msg} (code: {error_code})", xbmc.LOGWARNING)
                        
                        # If it's a credential error, don't try other data centers
                        if error_code in [403005, 403042, 403043]:  # Invalid credentials errors
                            xbmc.log("plugin.video.rtve - Invalid credentials, not trying other data centers", xbmc.LOGERROR)
                            return False
                        
                        continue
                        
                except json.JSONDecodeError:
                    xbmc.log(f"plugin.video.rtve - Invalid JSON response from {data_center}", xbmc.LOGWARNING)
                    continue
            
            # If we get here, none of the data centers worked
            xbmc.log("plugin.video.rtve - Failed to authenticate with any Gigya data center", xbmc.LOGERROR)
            return False
                
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Gigya login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def _direct_rtve_login(self, username: str, password: str) -> bool:
        """
        Direct RTVE authentication without Gigya
        
        Args:
            username: Username/email
            password: Password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            xbmc.log("plugin.video.rtve - Attempting direct RTVE login", xbmc.LOGDEBUG)
            
            # RTVE login endpoints to try in order of preference
            login_endpoints = [
                {
                    'url': 'https://www.rtve.es/usuarios/acceso/login/',
                    'method': 'POST',
                    'content_type': 'application/x-www-form-urlencoded'
                },
                {
                    'url': 'https://secure2.rtve.es/usuarios/acceso/login/',
                    'method': 'POST',
                    'content_type': 'application/x-www-form-urlencoded'
                },
                {
                    'url': 'https://www.rtve.es/api/usuarios/login',
                    'method': 'POST', 
                    'content_type': 'application/json'
                },
                {
                    'url': 'https://www.rtve.es/api/auth/login',
                    'method': 'POST',
                    'content_type': 'application/json'
                }
            ]
            
            # Different data formats to try
            login_data_formats = [
                # Standard form data
                {'username': username, 'password': password},
                {'email': username, 'password': password},
                {'user': username, 'password': password},
                {'login': username, 'password': password},
                # With additional common fields
                {'username': username, 'password': password, 'remember': '1'},
                {'email': username, 'password': password, 'remember': 'true'},
                # CSRF token placeholder (will be filled if found)
                {'username': username, 'password': password, 'csrf_token': ''},
                {'email': username, 'password': password, '_token': ''}
            ]
            
            for endpoint in login_endpoints:
                login_url = endpoint['url']
                content_type = endpoint['content_type']
                
                xbmc.log(f"plugin.video.rtve - Trying direct login endpoint: {login_url}", xbmc.LOGDEBUG)
                
                # First, try to get the login page to extract any CSRF tokens or form data
                csrf_token = self._extract_csrf_token(login_url)
                
                for login_data in login_data_formats:
                    try:
                        # Add CSRF token if found and field exists
                        if csrf_token and ('csrf_token' in login_data or '_token' in login_data):
                            if 'csrf_token' in login_data:
                                login_data['csrf_token'] = csrf_token
                            if '_token' in login_data:
                                login_data['_token'] = csrf_token
                        
                        # Prepare request data based on content type
                        if content_type == 'application/json':
                            data = json.dumps(login_data).encode('utf-8')
                            headers = {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'Referer': 'https://www.rtve.es/usuarios/acceso/login/',
                                'Origin': 'https://www.rtve.es',
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        else:
                            data = urllib.parse.urlencode(login_data).encode('utf-8')
                            headers = {
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Accept': 'application/json, text/html, */*',
                                'Referer': 'https://www.rtve.es/usuarios/acceso/login/',
                                'Origin': 'https://www.rtve.es'
                            }
                        
                        response_text = self._make_request(login_url, data=data, headers=headers, timeout=15, max_retries=2)
                        
                        if not response_text:
                            continue
                        
                        # Check if login was successful
                        if self._check_login_success(response_text, login_url):
                            # Update session cookies
                            for cookie in self.cookie_jar:
                                self.session_cookies[cookie.name] = cookie.value
                            
                            self._save_cookies()
                            xbmc.log(f"plugin.video.rtve - Direct RTVE login successful via {login_url}!", xbmc.LOGINFO)
                            return True
                            
                    except Exception as e:
                        xbmc.log(f"plugin.video.rtve - Error with login data format: {str(e)}", xbmc.LOGDEBUG)
                        continue
            
            xbmc.log("plugin.video.rtve - All direct RTVE login methods failed", xbmc.LOGWARNING)
            return False
            
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Direct RTVE login error: {str(e)}", xbmc.LOGERROR)
            return False
    
    def _extract_csrf_token(self, login_url: str) -> Optional[str]:
        """
        Extract CSRF token from login page
        
        Args:
            login_url: Login page URL
            
        Returns:
            CSRF token if found, None otherwise
        """
        try:
            # Get the login page to look for CSRF tokens
            if 'api' not in login_url:  # Only for HTML pages, not API endpoints
                page_content = self._make_request(login_url, timeout=10, max_retries=1)
                if page_content:
                    # Look for common CSRF token patterns
                    csrf_patterns = [
                        r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
                        r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
                        r'csrf["\']:\s*["\']([^"\']+)["\']',
                        r'_token["\']:\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in csrf_patterns:
                        match = re.search(pattern, page_content, re.IGNORECASE)
                        if match:
                            token = match.group(1)
                            xbmc.log(f"plugin.video.rtve - Found CSRF token: {token[:10]}...", xbmc.LOGDEBUG)
                            return token
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error extracting CSRF token: {str(e)}", xbmc.LOGDEBUG)
        
        return None
    
    def _check_login_success(self, response_text: str, login_url: str) -> bool:
        """
        Check if login response indicates success
        
        Args:
            response_text: Response content
            login_url: Login URL used
            
        Returns:
            True if login appears successful, False otherwise
        """
        try:
            response_lower = response_text.lower()
            
            # Strong success indicators
            strong_success_indicators = [
                'dashboard', 'perfil', 'mi cuenta', 'logout', 'cerrar sesion',
                'bienvenido', 'welcome', 'usuario logueado', 'sesion iniciada'
            ]
            
            # JSON success indicators
            json_success_indicators = [
                'access_token', 'token', 'session_token', 'auth_token',
                'user_id', 'usuario', 'profile'
            ]
            
            # Error indicators
            error_indicators = [
                'error', 'incorrecto', 'invalid', 'failed', 'denied',
                'usuario no encontrado', 'contraseña incorrecta', 'credenciales',
                'authentication failed', 'login failed'
            ]
            
            # Check for strong success indicators
            has_strong_success = any(indicator in response_lower for indicator in strong_success_indicators)
            has_error = any(indicator in response_lower for indicator in error_indicators)
            
            # Try to parse as JSON for structured response
            try:
                response_data = json.loads(response_text)
                xbmc.log(f"plugin.video.rtve - JSON response received from {login_url}", xbmc.LOGDEBUG)
                
                # Check for explicit success/error in JSON
                if response_data.get('success') is True or response_data.get('status') == 'success':
                    return True
                elif response_data.get('error') or response_data.get('status') == 'error':
                    return False
                
                # Check for authentication tokens or user data
                has_json_success = any(key in response_data for key in json_success_indicators)
                if has_json_success:
                    return True
                    
            except json.JSONDecodeError:
                # Not JSON, continue with text analysis
                pass
            
            # Check for redirects to authenticated areas (status codes handled by _make_request)
            if 'location.href' in response_lower or 'window.location' in response_lower:
                # Check if redirect is to an authenticated area
                redirect_patterns = [
                    r'location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'window\.location\s*=\s*["\']([^"\']+)["\']'
                ]
                for pattern in redirect_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        redirect_url = match.group(1).lower()
                        if any(auth_path in redirect_url for auth_path in ['dashboard', 'profile', 'cuenta', 'usuario']):
                            return True
            
            # Final decision
            if has_strong_success and not has_error:
                return True
            
            # If we have cookies set, that might indicate successful login
            if len(self.cookie_jar) > 0:
                # Check for authentication-related cookies
                auth_cookies = ['session', 'auth', 'login', 'token', 'user']
                for cookie in self.cookie_jar:
                    if any(auth_name in cookie.name.lower() for auth_name in auth_cookies):
                        xbmc.log(f"plugin.video.rtve - Found authentication cookie: {cookie.name}", xbmc.LOGDEBUG)
                        return True
            
            return False
            
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error checking login success: {str(e)}", xbmc.LOGDEBUG)
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

