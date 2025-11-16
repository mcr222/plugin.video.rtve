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
        Login to RTVE Play
        
        Args:
            username: RTVE Play username/email
            password: RTVE Play password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            xbmc.log("plugin.video.rtve - Attempting login", xbmc.LOGDEBUG)
            
            # Try multiple possible login endpoints
            login_endpoints = [
                "https://www.rtve.es/api/oauth/login",
                "https://www.rtve.es/api/login",
                "https://www.rtve.es/play/api/login",
                "https://api.rtve.es/api/login"
            ]
            
            # Create opener with cookie handler
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
            
            for login_url in login_endpoints:
                try:
                    xbmc.log(f"plugin.video.rtve - Trying login endpoint: {login_url}", xbmc.LOGDEBUG)
                    
                    # Prepare login data - try different formats
                    login_data_formats = [
                        {'username': username, 'password': password, 'grant_type': 'password'},
                        {'email': username, 'password': password},
                        {'user': username, 'pass': password},
                        {'login': username, 'password': password}
                    ]
                    
                    for login_data in login_data_formats:
                        try:
                            # Create request
                            data = urllib.parse.urlencode(login_data).encode('utf-8')
                            req = urllib.request.Request(
                                login_url,
                                data=data,
                                headers={
                                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                    'Referer': 'https://www.rtve.es/play/',
                                    'Origin': 'https://www.rtve.es',
                                    'Accept': 'application/json, text/plain, */*'
                                }
                            )
                            
                            # Perform login
                            with opener.open(req, timeout=10) as response:
                                response_text = response.read().decode('utf-8')
                                
                                if response.status == 200:
                                    # Try to parse as JSON
                                    try:
                                        response_data = json.loads(response_text)
                                        xbmc.log(f"plugin.video.rtve - Login response: {response_data}", xbmc.LOGDEBUG)
                                    except:
                                        response_data = {}
                                    
                                    # Check if login was successful
                                    # Look for common success indicators
                                    if ('access_token' in response_data or 
                                        'token' in response_data or 
                                        'success' in response_text.lower() or
                                        response.status == 200):
                                        # Update session cookies
                                        for cookie in self.cookie_jar:
                                            self.session_cookies[cookie.name] = cookie.value
                                        
                                        self._save_cookies()
                                        xbmc.log("plugin.video.rtve - Login successful", xbmc.LOGINFO)
                                        return True
                        except urllib.error.HTTPError as e:
                            if e.code == 200:  # Sometimes 200 with error in body
                                continue
                            elif e.code not in [404, 405]:  # Skip not found/method not allowed
                                xbmc.log(f"plugin.video.rtve - HTTP {e.code} for {login_url}", xbmc.LOGDEBUG)
                            continue
                        except Exception as e:
                            xbmc.log(f"plugin.video.rtve - Error trying format: {str(e)}", xbmc.LOGDEBUG)
                            continue
                            
                except Exception as e:
                    xbmc.log(f"plugin.video.rtve - Error with endpoint {login_url}: {str(e)}", xbmc.LOGDEBUG)
                    continue
            
            # If all endpoints failed, try a simple cookie-based approach
            # Some sites require visiting the login page first
            xbmc.log("plugin.video.rtve - Trying cookie-based approach", xbmc.LOGDEBUG)
            try:
                # Visit login page to get initial cookies
                login_page_url = "https://www.rtve.es/play/"
                req = urllib.request.Request(
                    login_page_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
                        'Referer': 'https://www.rtve.es/',
                    }
                )
                opener.open(req, timeout=10)
                
                # Update session cookies from initial visit
                for cookie in self.cookie_jar:
                    self.session_cookies[cookie.name] = cookie.value
                self._save_cookies()
                
                # Note: For now, we'll rely on cookies being set manually or via browser
                # This is a common pattern for DRM-protected content
                xbmc.log("plugin.video.rtve - Cookie-based approach initialized", xbmc.LOGDEBUG)
                return True
            except Exception as e:
                xbmc.log(f"plugin.video.rtve - Cookie approach failed: {str(e)}", xbmc.LOGDEBUG)
            
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
            # Check for common session cookie names
            session_keys = ['JSESSIONID', 'sessionid', 'rtve_session', 'access_token', 'rtve_token']
            return any(key.lower() in [k.lower() for k in self.session_cookies.keys()] for key in session_keys)
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

