# Gigya Data Center Authentication Fix

## Problem Description

The RTVE plugin was failing to authenticate with Gigya due to error code **301001: "Invalid data center"**. This error occurs when an API key is configured for a specific Gigya data center, but requests are being made to a different data center endpoint.

### Error Log Analysis
```
plugin.video.rtve - Gigya response status: 301001
plugin.video.rtve - Gigya login failed: Invalid data center
```

## Root Cause

Gigya operates multiple data centers globally:
- **US Data Center**: `us1.gigya.com` (default/legacy `accounts.gigya.com`)
- **EU Data Center**: `eu1.gigya.com` 
- **AU Data Center**: `au1.gigya.com`

The original code was hardcoded to use `accounts.gigya.com` (US data center), but RTVE's API key is configured for the European data center since RTVE is a Spanish broadcaster.

## Solution Implemented

### 1. Automatic Data Center Detection
The authentication system now tries multiple data centers in order of likelihood:

```python
data_centers = [
    'eu1.gigya.com',  # European data center (most likely for RTVE)
    'us1.gigya.com',  # US data center
    'au1.gigya.com'   # Australian data center
]
```

### 2. Smart Error Handling
- **301001 (Invalid data center)**: Continue to next data center
- **0 (Success)**: Stop and return success
- **403005, 403042, 403043 (Invalid credentials)**: Stop trying (credentials issue)
- **Other errors**: Continue to next data center

### 3. Data Center Caching
Once a successful data center is found, it's stored in cookies for future use:
```python
self.session_cookies['gigya_data_center'] = data_center
```

### 4. Optimized Retry Logic
- First attempt uses previously successful data center (if available)
- Falls back to full data center detection if stored one fails
- Reduces unnecessary requests for subsequent logins

## Code Changes

### Modified Files
- `resources/lib/utils/Auth.py`: Enhanced `_gigya_login()` method with data center detection

### New Methods Added
- `_gigya_login_single_datacenter()`: Authenticate using specific data center
- Enhanced logging throughout the authentication process

## Benefits

1. **Resolves 301001 Error**: Automatically finds correct data center
2. **Improved Performance**: Caches successful data center for future use
3. **Better Debugging**: Comprehensive logging shows which data center is being used
4. **Robust Fallback**: Handles various error scenarios gracefully
5. **Future-Proof**: Works with any Gigya data center configuration

## Testing

The fix has been tested with a comprehensive test suite that validates:
- Error code handling logic
- Data center priority ordering
- URL construction
- Fallback mechanisms

## Usage

No configuration changes are required. The plugin will automatically:
1. Try the EU data center first (most likely for RTVE)
2. Fall back to US and AU data centers if needed
3. Store the successful data center for future logins
4. Provide detailed logging for troubleshooting

## Logging Output

With the fix, users will see logs like:
```
plugin.video.rtve - Attempting Gigya authentication with data center detection
plugin.video.rtve - Trying Gigya data center: eu1.gigya.com
plugin.video.rtve - Gigya login successful using data center: eu1.gigya.com
```

This makes it easy to verify which data center is being used and troubleshoot any remaining issues.