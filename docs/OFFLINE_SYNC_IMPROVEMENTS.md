# Offline Sync Improvements

## Changes Made

### 1. Manual Sync Button
**Location**: Yellow offline banner (top of scanner page)

**Features**:
- Appears when online with pending scans
- Green button with sync icon
- Spinning animation during sync
- Allows manual trigger if auto-sync fails

**Usage**: Click "Sync Now" button when you see pending scans

### 2. Enhanced Console Logging
**Purpose**: Debug sync issues in real-time

**Log Messages**:
- `[OFFLINE SYNC] Starting sync. Queue length: X Online: true/false`
- `[OFFLINE SYNC] Syncing item: ID Student: XXX Event: YYY`
- `[OFFLINE SYNC] POST to: URL Body: {...}`
- `[OFFLINE SYNC] Success for item: ID Response: {...}`
- `[OFFLINE SYNC] Failed for item: ID Status: XXX`
- `[OFFLINE SYNC] All scans synced successfully`

**How to View**:
1. Open browser console (F12 or Ctrl+Shift+I)
2. Go to Console tab
3. Scan QR codes while offline
4. Watch for `[OFFLINE SYNC]` messages when back online

### 3. Improved Banner Display
**Changes**:
- Shows manual sync button when online with pending scans
- Hides button when offline or no pending scans
- Better visual feedback during sync process

## Testing the Offline Sync

### Test Scenario 1: Normal Offline/Online Cycle
1. Open scanner page
2. Open browser console (F12)
3. Disconnect internet (turn off WiFi or unplug ethernet)
4. Scan 2-3 student QR codes
5. Verify banner shows "X scan(s) pending sync"
6. Reconnect internet
7. Watch console for `[OFFLINE SYNC]` messages
8. Verify scans appear in Live Entries panel

### Test Scenario 2: Manual Sync
1. Have pending scans in queue
2. Be online
3. Click "Sync Now" button in yellow banner
4. Watch console for sync progress
5. Verify scans sync to server

### Test Scenario 3: Check IndexedDB Storage
1. Open DevTools (F12)
2. Go to Application tab
3. Expand IndexedDB in left sidebar
4. Click on "GateOfflineDB" > "scans"
5. View stored offline scans
6. After sync, verify scans are removed

## Troubleshooting with New Tools

### Problem: Scans not queuing when offline
**Debug Steps**:
1. Check console: `console.log(navigator.onLine)` - should be `false`
2. Check console: `console.log(_offlineQueueCache)` - should show scans
3. Check IndexedDB: DevTools > Application > IndexedDB > GateOfflineDB
4. Look for errors in console when scanning

### Problem: Scans queued but not syncing
**Debug Steps**:
1. Check console for `[OFFLINE SYNC]` messages
2. Look for error messages in console
3. Check Network tab for failed POST requests
4. Click "Sync Now" button manually
5. Check if server is reachable

### Problem: Sync fails with errors
**Debug Steps**:
1. Check console for `[OFFLINE SYNC] Failed for item` messages
2. Check Network tab for HTTP status codes (500, 403, etc.)
3. Verify CSRF token is valid
4. Check server logs for backend errors

## Expected Console Output (Normal Flow)

```
[OFFLINE SYNC] Initial queue load. Length: 0 Online: true
[User goes offline and scans 2 QR codes]
[User goes back online]
[OFFLINE SYNC] Network online event fired
[OFFLINE SYNC] Queue loaded from DB. Length: 2
[OFFLINE SYNC] Starting sync. Queue length: 2 Online: true
[OFFLINE SYNC] Syncing item: 1 Student: 2021-0001 Event: null
[OFFLINE SYNC] POST to: /gate/save-scan/ Body: {student_id: "2021-0001", ...}
[OFFLINE SYNC] Success for item: 1 Response: {success: true, ...}
[OFFLINE SYNC] Syncing item: 2 Student: 2021-0002 Event: null
[OFFLINE SYNC] POST to: /gate/save-scan/ Body: {student_id: "2021-0002", ...}
[OFFLINE SYNC] Success for item: 2 Response: {success: true, ...}
[OFFLINE SYNC] All scans synced successfully
```

## Browser Compatibility Notes

### Chrome/Edge
- Full support for IndexedDB and online events
- Auto-sync works reliably

### Firefox
- Full support for IndexedDB and online events
- Auto-sync works reliably

### Safari
- IndexedDB supported
- `online` event may not fire reliably
- **Workaround**: Use manual sync button or refresh page after reconnecting

## Next Steps

If sync still doesn't work after these improvements:

1. **Check the console logs** - They will show exactly where the process fails
2. **Test with manual sync button** - Bypasses auto-sync issues
3. **Check IndexedDB** - Verify scans are being stored
4. **Check Network tab** - See if requests reach the server
5. **Check server logs** - See if backend is processing requests

## Support

If you continue to experience issues:
1. Open browser console (F12)
2. Reproduce the issue
3. Copy all `[OFFLINE SYNC]` messages
4. Share the console output for diagnosis

