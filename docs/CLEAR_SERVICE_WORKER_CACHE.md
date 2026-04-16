# Clear Service Worker Cache - CRITICAL

## Problem

Your scanner page uses a **Service Worker** that caches the JavaScript code. This means even after I fix the code, your browser continues to use the old cached version.

## Solution: Clear Service Worker Cache

### Method 1: Using DevTools (Recommended)

1. Open your scanner page
2. Press **F12** (open DevTools)
3. Go to **Application** tab
4. In left sidebar, click **Service Workers**
5. You'll see: `https://unsurrendering-implicably-alfreda.ngrok-free.dev/gate/sw.js`
6. Click **"Unregister"** button next to it
7. In left sidebar, click **Cache Storage**
8. Right-click each cache and select **"Delete"**
9. Close DevTools
10. **Hard refresh**: Ctrl+Shift+R (or Ctrl+F5)

### Method 2: Using Console Command

1. Open Console (F12)
2. Paste this command and press Enter:

```javascript
navigator.serviceWorker.getRegistrations().then(function(registrations) {
  for(let registration of registrations) {
    registration.unregister();
    console.log('Unregistered:', registration.scope);
  }
  console.log('All service workers unregistered. Now refresh the page with Ctrl+Shift+R');
});
```

3. Wait for message: "All service workers unregistered"
4. **Hard refresh**: Ctrl+Shift+R

### Method 3: Clear All Browser Data

1. Press **Ctrl+Shift+Delete**
2. Select:
   - ✅ Cached images and files
   - ✅ Cookies and other site data
3. Time range: **Last hour**
4. Click **"Clear data"**
5. Close and reopen browser
6. Go back to scanner page

## How to Verify Changes Are Loaded

After clearing cache, open Console (F12) and type:

```javascript
console.log('currentScanMode defined:', typeof currentScanMode !== 'undefined');
```

**Expected result**: `currentScanMode defined: true`

If it says `false`, the old code is still cached.

## Test Offline Scanning

After clearing cache:

1. Open Console (F12)
2. Disconnect WiFi
3. Scan a QR code
4. **Expected console output**:
```
[SCAN] Processing: [student-id] navigator.onLine: false
[SCAN] Checking offline status. navigator.onLine: false
[OFFLINE SCAN] Detected offline. Queuing scan: ...
[OFFLINE SCAN] Queue item: {qr: "...", ...}
[OFFLINE SCAN] addToOfflineQueue result: {ok: true, reason: "saved"}
[OFFLINE SCAN] Successfully queued. Total pending: 1
```

5. **Expected on screen**:
   - Green success message
   - "Saved offline (1 scan(s) pending sync). Will sync when online."
   - Success beep sound

## Why This Happens

Service Workers are designed to make web apps work offline by caching resources. However, this means:
- Code changes don't appear immediately
- You must manually clear the cache to see updates
- The service worker version needs to be bumped (currently v=3)

## Permanent Solution

I can bump the service worker version to force all users to get the new code. But for now, you need to manually clear your cache.

