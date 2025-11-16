import urllib.request, urllib.parse, urllib.error
import json
import time
import socket
from typing import Any, Optional, Dict

import xbmc

# Import auth module - use lazy import to avoid circular dependencies
_auth_instance = None

def _get_auth():
    """Get auth instance (lazy initialization)"""
    global _auth_instance
    if _auth_instance is None:
        try:
            from resources.lib.utils.Auth import RTVEAuth
            _auth_instance = RTVEAuth()
        except Exception as e:
            xbmc.log(f"plugin.video.rtve - Error initializing auth: {str(e)}", xbmc.LOGERROR)
    return _auth_instance


def buildUrl(query, base_url):
    return base_url + '?' + urllib.parse.urlencode(query)


class NetworkError(Exception):
    """Custom exception for network-related errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
    
    def __str__(self):
        if self.status_code:
            return f"{super().__str__()} (Status: {self.status_code})"
        return super().__str__()


def getJsonData(apiUrl: str, max_retries: Optional[int] = None, retry_delay: Optional[int] = None, use_auth: bool = True) -> Dict[str, Any]:
    """
    Fetch JSON data from a URL with retry logic and proper error handling.

    Args:
        apiUrl: The URL to fetch data from
        max_retries: Maximum number of retry attempts (uses config default if None)
        retry_delay: Delay between retries in seconds (uses config default if None)
        use_auth: Whether to include authentication headers (default: True)

    Returns:
        Dict containing the parsed JSON data

    Raises:
        NetworkError: If all retry attempts fail or other network issues occur
    """
    # Get network configuration
    try:
        from resources.lib.utils.NetworkConfig import network_config
        timeout = network_config.get_timeout()
        if max_retries is None:
            max_retries = network_config.get_max_retries()
        if retry_delay is None:
            retry_delay = network_config.get_retry_delay()
    except ImportError:
        timeout = 30
        if max_retries is None:
            max_retries = 3
        if retry_delay is None:
            retry_delay = 2
    
    # Get authentication headers if available
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    
    if use_auth:
        auth = _get_auth()
        if auth:
            auth_headers = auth.get_auth_headers()
            headers.update(auth_headers)

    for attempt in range(max_retries + 1):
        try:
            xbmc.log(f"plugin.video.rtve - Fetching JSON from {apiUrl} (attempt {attempt + 1}/{max_retries + 1})", xbmc.LOGDEBUG)
            
            req = urllib.request.Request(apiUrl, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    content = response.read()
                    
                    # Handle gzip encoding
                    if response.info().get('Content-Encoding') == 'gzip':
                        import gzip
                        content = gzip.decompress(content)
                    elif response.info().get('Content-Encoding') == 'deflate':
                        import zlib
                        content = zlib.decompress(content)
                    
                    result = json.loads(content.decode('utf-8'))
                    xbmc.log(f"plugin.video.rtve - Successfully fetched JSON data", xbmc.LOGDEBUG)
                    return result
                else:
                    raise NetworkError(f"Server returned status code: {response.status}")

        except (urllib.error.URLError, socket.error) as e:
            is_last_attempt = attempt == max_retries
            
            if "timed out" in str(e).lower():
                error_msg = f"Request timed out on attempt {attempt + 1}/{max_retries + 1}: {str(e)}"
            else:
                error_msg = f"Network error on attempt {attempt + 1}/{max_retries + 1}: {str(e)}"

            if is_last_attempt:
                xbmc.log(f"plugin.video.rtve - Error with content type application/json: The read operation timed out", xbmc.LOGERROR)
                raise NetworkError(f"Failed to fetch data after {max_retries + 1} attempts: {str(e)}")
            else:
                xbmc.log(error_msg, xbmc.LOGWARNING)
                # Exponential backoff with jitter
                import random
                delay = retry_delay * (2 ** attempt) + random.uniform(0, 1)
                xbmc.log(f"plugin.video.rtve - Waiting {delay:.1f}s before retry...", xbmc.LOGDEBUG)
                time.sleep(delay)

        except json.JSONDecodeError as e:
            raise NetworkError(f"Failed to parse JSON response: {str(e)}")

        except Exception as e:
            raise NetworkError(f"Unexpected error while fetching data: {str(e)}")


def safe_request(url: str) -> Optional[str]:
    """
    Make a safe HTTP request that handles common network errors

    Args:
        url: The URL to request

    Returns:
        Optional[str]: The response content if successful, None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        xbmc.log(f"Error making request to {url}: {str(e)}", xbmc.LOGERROR)
        return None