"""
Network configuration module for RTVE Play
Handles timeout settings and network parameters
"""
import xbmcaddon
import xbmc


class NetworkConfig:
    """Network configuration management"""
    
    def __init__(self):
        self.addon = xbmcaddon.Addon()
    
    def get_timeout(self) -> int:
        """Get network timeout from settings"""
        try:
            timeout = int(self.addon.getSetting('network_timeout'))
            return max(10, min(timeout, 120))  # Clamp between 10-120 seconds
        except (ValueError, TypeError):
            return 15  # Reduced default timeout for faster failures
    
    def get_max_retries(self) -> int:
        """Get maximum retry attempts from settings"""
        try:
            retries = int(self.addon.getSetting('max_retries'))
            return max(1, min(retries, 5))  # Clamp between 1-5 retries
        except (ValueError, TypeError):
            return 2  # Reduced default retries
    
    def get_retry_delay(self) -> float:
        """Get retry delay from settings"""
        try:
            delay = float(self.addon.getSetting('retry_delay'))
            return max(0.5, min(delay, 10.0))  # Clamp between 0.5-10 seconds
        except (ValueError, TypeError):
            return 1.0  # Reduced default delay
    
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled"""
        try:
            return self.addon.getSettingBool('debug_logging')
        except:
            return False
    
    def log_network_settings(self):
        """Log current network settings"""
        if self.is_debug_enabled():
            xbmc.log(f"plugin.video.rtve - Network timeout: {self.get_timeout()}s", xbmc.LOGDEBUG)
            xbmc.log(f"plugin.video.rtve - Max retries: {self.get_max_retries()}", xbmc.LOGDEBUG)
            xbmc.log(f"plugin.video.rtve - Retry delay: {self.get_retry_delay()}s", xbmc.LOGDEBUG)


# Global instance
network_config = NetworkConfig()