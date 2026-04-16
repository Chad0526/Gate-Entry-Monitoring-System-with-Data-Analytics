# Offline Scan Fix - April 3, 2026

## Problem

When scanning QR codes while offline:
- No message appeared saying scan was saved offline
- IndexedDB remained empty (no scans queued)
- Scans were not being stored for later sync

## Root Cause

**Missing Variable**: The variable `currentScanMode` was used but never defined, causing JavaScript errors that prevented offline queue from working.

## Fix Applied

### 1. Defined `currentScanMode` Variable
**Location**: Line ~4630 in `templates/gate/gate_scan.html`

```javascript
// Current scan mode (IN/OUT) - defaults to IN, server determines actual mode based on last scan
var currentScanMode = 'IN';
```

**Why**: The offline queue code referenced `currentScanMode` but it was undefined, causing the offline save to fail silently.

### 2. Added Enhanced Console Logging
Added detailed logging to track offline scan process:

```javascript
console.log('[SCAN] Processing:', qr_or_student_id, 'navigator.onLine:', navigator.onLine);
console.log('[OFFLINE SCAN] Detected offline. Queuing scan:', ...);
console.log('[OFFLINE SCAN] Queue item:', queueItem);
console.log('[OFFLINE SCAN] addToOfflineQueue result:', result);
console.log('[OFFLINE SCAN] Successfully queued. Total pending:', n);
```

## How to Test

### Test 1: Verify Fix Works
1. Open scanner page
2. Open browser console (F12)
3. **Disconnect internet** (turn off WiFi)
4. Scan a QR code
5. **Expected Results**:
   - Console shows: `[SCAN] Processing: [student-id] navigator.onLine: false`
   - Console shows: `[OFFLINE SCAN] Detected offline. Queuing scan: ...`
   - Console shows: `[OFFLINE SCAN] Successfully queued. Total pending: 1`
   - Green success message: "Saved offline (1 scan(s) pending sync). Will sync when online."
   - Success beep plays
   - Yellow banner shows "1 scan(s) pending sync"

### Test 2: Verify IndexedDB Storage
1. After scanning offline (Test 1)
2. Open DevTools (F12) → **Application** tab
3. Expand **IndexedDB** → **GateOfflineDB** → **scans**
4. **Expected**: You should see your scan stored with:
   - `qr`: Student ID
   - `scan_type`: "IN"
   - `event_id`: null (or event ID if event scan)
   - `client_ts`: Timestamp

### Test 3: Verify Auto-Sync
1. Have pending scans from Test 1
2. **Reconnect internet** (turn WiFi back on)
3. **Expected Results**:
   - Console shows: `[OFFLINE SYNC] Network online event fired`
   - Console shows: `[OFFLINE SYNC] Starting sync. Queue length: 1`
   - Console shows: `[OFFLINE SYNC] Syncing item: ...`
   - Console shows: `[OFFLINE SYNC] Success for item: ...`
   - Console shows: `[OFFLINE SYNC] All scans synced successfully`
   - Notification: "All offline scans synced to server."
   - Yellow banner disappears
   - Scans appear in Live Entries panel

## Technical Details

### Why `currentScanMode = 'IN'`?

The system automatically determines whether a scan should be IN or OUT based on the student's last scan status on the server. For offline scans, we default to 'IN' and let the server correct it when syncing.

**Server-side logic**:
- If student has no entry today → IN
- If student already IN → OUT
- If student already OUT → OUT (duplicate)

### Browser Compatibility

The fix works on all modern browsers:
- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ Opera

## Troubleshooting

### Issue: Still not working after fix
**Solution**: Hard refresh the page (Ctrl+Shift+R) to clear cached JavaScript

### Issue: Console shows "navigator.onLine: true" when offline
**Solution**: 
- `navigator.onLine` only detects network interface status, not actual internet connectivity
- If you disconnect WiFi, it should show `false`
- If you block the server in firewall, it might still show `true`
- The system also has fallback: failed AJAX requests trigger offline queue

### Issue: Scans queue but don't sync
**Solution**: Check the sync logs in console and refer to `OFFLINE_SYNC_DIAGNOSTIC.md`

## Files Modified

1. `templates/gate/gate_scan.html`
   - Added `currentScanMode` variable definition
   - Added console logging for offline scan process
   - Added console logging for sync process

## Related Documentation

- `docs/OFFLINE_SYNC_DIAGNOSTIC.md` - Troubleshooting guide
- `docs/OFFLINE_SYNC_IMPROVEMENTS.md` - Testing and usage guide

