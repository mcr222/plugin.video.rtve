# RTVE Play DRM Authentication Guide

This guide explains how to resolve DRM authentication issues with the RTVE Kodi plugin.

## Problem Description

The error you're experiencing:
```
LogDecryptError: Decrypt failed with error code: 2 and KID: 1d62afdcff6d29f606fa4baface564ed
Decrypt Sample returns failure!
```

This indicates that the Widevine DRM system is failing to decrypt content due to authentication issues.

## Solution Overview

The plugin has been enhanced with improved authentication support for RTVE Play's mandatory registration system (implemented February 2024).

## Step-by-Step Solution

### 1. Install Required Dependencies

Ensure you have the following Kodi addons installed:
- `inputstream.adaptive` (for DRM playback)
- `script.module.inputstreamhelper` (already in addon.xml)

### 2. Login to RTVE Play

1. Open the RTVE plugin in Kodi
2. Select "Login to RTVE Play" from the main menu
3. Enter your RTVE Play username/email and password
4. The plugin will attempt to authenticate with RTVE's servers

### 3. Verify Authentication

Use the debug feature to check your authentication status:
1. Select "Debug Authentication" from the main menu
2. Review the authentication information displayed
3. Test DRM authentication with a specific video ID if needed

### 4. Troubleshooting

If authentication fails, try these steps:

#### Manual Cookie Authentication (Alternative Method)
If automatic login doesn't work, you can manually set up authentication:

1. Open a web browser and go to https://www.rtve.es/play/
2. Login with your RTVE Play account
3. The plugin will attempt to use session cookies for authentication

#### Check Debug Information
Use the "Debug Authentication" option to see:
- Login status
- Available cookies
- RTVE connectivity
- Token API accessibility

#### Common Issues and Solutions

**Issue**: "Authentication required" error
**Solution**: Ensure you're logged in using the "Login to RTVE Play" option

**Issue**: "Content not found" error
**Solution**: The video may not be available or may have been removed

**Issue**: "Network error" or timeout errors
**Solution**: 
1. Check your internet connection
2. Go to Plugin Settings → Network Settings
3. Increase "Network Timeout" (try 60-120 seconds)
4. Increase "Maximum Retries" (try 5-10)
5. Increase "Retry Delay" (try 3-5 seconds)

**Issue**: DRM decryption still fails after login
**Solution**: 
1. Try logging out and logging back in
2. Clear Kodi cache
3. Restart Kodi
4. Use the debug feature to test specific video IDs

### 5. Network Configuration

If you're experiencing frequent timeout errors, you can adjust network settings:

1. Open Kodi Settings
2. Go to Add-ons → My add-ons → Video add-ons → RTVE
3. Click "Configure"
4. Go to "Network Settings" tab
5. Adjust the following settings:
   - **Network Timeout**: Time to wait for server response (10-120 seconds)
   - **Maximum Retries**: How many times to retry failed requests (1-10)
   - **Retry Delay**: Wait time between retries (1-10 seconds)
   - **Debug Logging**: Enable detailed logging for troubleshooting

**Recommended settings for slow connections:**
- Network Timeout: 60 seconds
- Maximum Retries: 5
- Retry Delay: 3 seconds

### 6. Advanced Troubleshooting

#### Enable Debug Logging
1. Go to Kodi Settings > System > Logging
2. Enable "Enable debug logging"
3. Try playing a video and check the Kodi log for detailed error messages

#### Check inputstream.adaptive
1. Ensure inputstream.adaptive is installed and enabled
2. Go to Add-ons > My add-ons > VideoPlayer InputStream > InputStream Adaptive
3. Make sure it's enabled

#### Widevine CDM
Some systems may need the Widevine CDM (Content Decryption Module):
1. This is usually installed automatically with inputstream.adaptive
2. On some systems, you may need to install it manually

## Technical Details

### Authentication Flow
1. Plugin visits RTVE login page to get CSRF tokens
2. Attempts login with multiple endpoint formats
3. Stores authentication cookies
4. Uses cookies for API requests and DRM license requests

### DRM Process
1. Request video token from RTVE API with authentication
2. Extract Widevine license URL from token response
3. Configure inputstream.adaptive with proper headers
4. Pass authentication to license server

### Supported Authentication Methods
- Username/password login
- Session cookie authentication
- Bearer token authentication
- CSRF token handling

## Error Codes Reference

- **Error Code 2**: Authentication/authorization failure
- **Error Code 401/403**: Unauthorized access
- **Error Code 404**: Content not found
- **Network errors**: Connectivity issues

## Getting Help

If you continue to experience issues:

1. Use the "Debug Authentication" feature and note the results
2. Check Kodi logs with debug logging enabled
3. Try the manual cookie authentication method
4. Report issues with debug information

## Recent Changes (November 2024)

- Enhanced authentication system for RTVE Play's mandatory registration
- Improved error handling and user feedback
- Added comprehensive debugging tools
- Better DRM license server authentication
- Support for multiple authentication endpoints

## Notes

- RTVE Play requires registration as of February 2024
- Some content may be geo-restricted
- DRM content requires a compatible system with Widevine support
- Authentication cookies are stored securely in Kodi's profile directory