# Offline Sync Diagnostic Guide

## Current Implementation

Your system uses a **hybrid offline storage approach**:
- **Primary**: IndexedDB (`GateOfflineDB`)
- **Fallback**: localStorage (`gate_offline_queue_fallback_v1`)
- **Queue Limit**: 500 scans (soft cap)

## How It Should Work

1. **Offline Scanning**: When `navigator.onLine` is false, scans are saved to IndexedDB
2. **Queue Display**: Yellow banner shows "X scan(s) pending sync"
3. **Auto-Sync**: When `online` event fires, `loadOfflineQueueFromDB()` loads queue and calls `syncOfflineQueue()`
4. **Sync Process**: Each scan is POSTed to server sequentially, removed from queue on success

## Common Issues & Solutions

### Issue 1: Scans Not Being Queued
**Symptoms**: No scans appear in offline queue when offline
**Causes**:
- `navigator.onLine` returns true even when server is unreachable
- Network timeout not triggering offline mode
- IndexedDB permission denied

**Debug Steps**:
1. Open browser console (F12)
2. Check: `console.log(navigator.onLine)` - should be `false` when offline
3. Check: `console.log(_offlineQueueCache)` - should show queued scans
4. Check IndexedDB: DevTools > Application > IndexedDB > GateOfflineDB

### Issue 2: Scans Queued But Not Syncing
**Symptoms**: Banner shows "X scans pending" but they don't sync when online
**Causes**:
- `online` event not firing
- Sync function failing silently
- CSRF token issues
- Server endpoint errors

**Debug Steps**:
1. Check console for sync errors
2. Check Network tab for failed POST requests
3. Manually trigger sync: `syncOfflineQueue()` in console

### Issue 3: Duplicate Detection Blocking Sync
**Symptoms**: Scans removed from queue but not appearing in server
**Causes**:
- Server returns "DUPLICATE" status
- Offline duplicate checking too aggressive

**Debug Steps**:
1. Check server response in Network tab
2. Look for "DUPLICATE" or "NOT_CHECKED_IN" responses

## Manual Sync Testing

Open browser console and run:

```javascript
// Check queue
console.log('Queue length:', _offlineQueueCache.length);
console.log('Queue items:', _offlineQueueCache);

// Check online status
console.log('Online:', navigator.onLine);

// Manually trigger sync
syncOfflineQueue();

// Watch for sync completion
console.log('After sync, queue length:', _offlineQueueCache.length);
```

## Browser Compatibility

| Browser | IndexedDB | localStorage | Auto-Sync |
|---------|-----------|--------------|-----------|
| Chrome  | ✅        | ✅           | ✅        |
| Firefox | ✅        | ✅           | ✅        |
| Safari  | ✅        | ✅           | ⚠️ (may need manual refresh) |
| Edge    | ✅        | ✅           | ✅        |

**Safari Note**: The `online` event may not fire reliably. Users may need to refresh the page after reconnecting.

## Recommended Fixes

### Fix 1: Add Manual Sync Button
Add a button to manually trigger sync when auto-sync fails.

### Fix 2: Enhanced Logging
Add console logging to track sync progress and failures.

### Fix 3: Periodic Sync Check
Check for pending scans every 30 seconds and auto-sync if online.

### Fix 4: Sync Status Indicator
Show detailed sync status (syncing, success, failed) for each scan.

## Next Steps

1. Test in browser console to identify which stage is failing
2. Check browser DevTools > Application > IndexedDB to see if scans are stored
3. Check Network tab to see if sync requests are being sent
4. Review server logs to see if requests are reaching the backend

