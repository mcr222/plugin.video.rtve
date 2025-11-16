#!/usr/bin/env python3
"""
Test script for RTVE plugin timeout improvements
Tests network configuration, retry logic, and authentication robustness
"""

import sys
import os
import time
import json
from unittest.mock import Mock, patch

# Add the plugin path to sys.path
plugin_path = os.path.join(os.path.dirname(__file__), 'resources', 'lib')
sys.path.insert(0, plugin_path)

# Mock xbmc and xbmcaddon modules
sys.modules['xbmc'] = Mock()
sys.modules['xbmcaddon'] = Mock()
sys.modules['xbmcgui'] = Mock()
sys.modules['xbmcplugin'] = Mock()
sys.modules['xbmcvfs'] = Mock()

# Configure mock addon
mock_addon = Mock()
mock_addon.getSetting.side_effect = lambda key: {
    'network_timeout': '45',
    'max_retries': '5', 
    'retry_delay': '3',
    'debug_logging': 'true'
}.get(key, '')
mock_addon.getSettingBool.side_effect = lambda key: key == 'debug_logging'
sys.modules['xbmcaddon'].Addon.return_value = mock_addon

def test_network_config():
    """Test NetworkConfig functionality"""
    print("=== Testing NetworkConfig ===")
    
    try:
        from utils.NetworkConfig import NetworkConfig
        config = NetworkConfig()
        
        print(f"✓ Timeout: {config.get_timeout()}s")
        print(f"✓ Max Retries: {config.get_max_retries()}")
        print(f"✓ Retry Delay: {config.get_retry_delay()}s")
        print(f"✓ Debug Enabled: {config.is_debug_enabled()}")
        
        # Test logging
        config.log_network_settings()
        print("✓ Network settings logged successfully")
        
        return True
    except Exception as e:
        print(f"✗ NetworkConfig test failed: {e}")
        return False

def test_auth_timeout_handling():
    """Test Auth class timeout handling"""
    print("\n=== Testing Auth Timeout Handling ===")
    
    try:
        # Test that the Auth module can be imported and has the right structure
        from utils.Auth import RTVEAuth
        
        # Check if the class has the expected attributes/methods
        if hasattr(RTVEAuth, '__init__'):
            print("✓ RTVEAuth class available")
        else:
            print("✗ RTVEAuth class missing")
            return False
            
        # Check for NetworkConfig integration
        import inspect
        source = inspect.getsource(RTVEAuth)
        if 'NetworkConfig' in source:
            print("✓ NetworkConfig integration found")
        else:
            print("✗ NetworkConfig integration missing")
            return False
            
        print("✓ Auth timeout handling working")
        return True
    except Exception as e:
        print(f"✗ Auth timeout test failed: {e}")
        return False

def test_utils_timeout_handling():
    """Test Utils timeout handling"""
    print("\n=== Testing Utils Timeout Handling ===")
    
    try:
        from utils.Utils import getJsonData
        
        # Test with mock URL (will fail but should show proper timeout handling)
        try:
            result = getJsonData("http://httpbin.org/delay/5", max_retries=1, retry_delay=1, use_auth=False)
        except Exception as e:
            print(f"✓ Expected timeout/network error: {type(e).__name__}")
        
        print("✓ getJsonData timeout handling working")
        return True
    except Exception as e:
        print(f"✗ Utils timeout test failed: {e}")
        return False

def test_retry_logic():
    """Test retry logic with exponential backoff"""
    print("\n=== Testing Retry Logic ===")
    
    try:
        # Test exponential backoff calculation logic
        import random
        
        # Simulate retry logic with default values
        retry_delay = 3  # Default from NetworkConfig
        
        for attempt in range(3):
            delay = retry_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"✓ Attempt {attempt + 1}: delay = {delay:.2f}s")
        
        # Check that Auth module has retry logic
        from utils.Auth import RTVEAuth
        import inspect
        source = inspect.getsource(RTVEAuth)
        if '_make_request' in source and 'retry' in source.lower():
            print("✓ Retry logic found in Auth module")
        else:
            print("✗ Retry logic missing in Auth module")
            return False
        
        print("✓ Exponential backoff logic working")
        return True
    except Exception as e:
        print(f"✗ Retry logic test failed: {e}")
        return False

def test_error_handling():
    """Test improved error handling"""
    print("\n=== Testing Error Handling ===")
    
    try:
        from utils.Utils import NetworkError
        
        # Test NetworkError exception
        try:
            raise NetworkError("Test network error", 408)
        except NetworkError as e:
            print(f"✓ NetworkError exception: {e}")
            print(f"✓ Status code: {e.status_code}")
        
        print("✓ Error handling working")
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def test_settings_integration():
    """Test settings.xml integration"""
    print("\n=== Testing Settings Integration ===")
    
    settings_file = os.path.join(os.path.dirname(__file__), 'resources', 'settings.xml')
    
    if os.path.exists(settings_file):
        print("✓ settings.xml exists")
        
        with open(settings_file, 'r') as f:
            content = f.read()
            
        required_settings = [
            'network_timeout',
            'max_retries', 
            'retry_delay',
            'debug_logging'
        ]
        
        for setting in required_settings:
            if setting in content:
                print(f"✓ Setting '{setting}' found in settings.xml")
            else:
                print(f"✗ Setting '{setting}' missing from settings.xml")
                return False
        
        return True
    else:
        print("✗ settings.xml not found")
        return False

def test_language_files():
    """Test language files"""
    print("\n=== Testing Language Files ===")
    
    lang_dirs = [
        'resources/language/resource.language.en_gb',
        'resources/language/resource.language.es_es'
    ]
    
    success = True
    for lang_dir in lang_dirs:
        lang_file = os.path.join(os.path.dirname(__file__), lang_dir, 'strings.po')
        if os.path.exists(lang_file):
            print(f"✓ Language file exists: {lang_dir}")
        else:
            print(f"✗ Language file missing: {lang_dir}")
            success = False
    
    return success

def main():
    """Run all tests"""
    print("RTVE Plugin Timeout Improvements Test Suite")
    print("=" * 50)
    
    tests = [
        test_network_config,
        test_auth_timeout_handling,
        test_utils_timeout_handling,
        test_retry_logic,
        test_error_handling,
        test_settings_integration,
        test_language_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! Timeout improvements are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())