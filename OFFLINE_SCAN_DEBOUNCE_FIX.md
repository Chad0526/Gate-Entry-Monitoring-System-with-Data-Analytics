# Offline Scan Debounce Fix

## Problem
In offline mode, the QR scanner was continuously scanning the same QR code multiple times, creating duplicate entries in the offline queue. This resulted in:
- Multiple beeps for a single scan
- Multiple "Scan saved to local database" notifications
- Queue filling up with duplicate entries
- Confusing user experience

## Root Cause
The QR scanner library (`html5-qrcode`) continuously reads QR codes as long as they're in view. Without a debounce mechanism, each frame that detects the QR code triggers a new scan event, causing the same code to be processed multiple times within seconds.

## Solution Implemented

### 1. Scan Cooldown Mechanism
Added a 3-second cooldown period between scans of the same QR code:

```javascript
// Debounce mechanism: prevent scanning the same QR code multiple times in quick succession
var lastScannedCode = null;
var lastScannedTime = 0;
var SCAN_COOLDOWN_MS = 3000; // 3 seconds cooldown between same QR code scans

function onScanSuccess(decodedText, decodedResult) {
  if (isProcessingScan) return;
  
  // Debounce: Check if this is the same code scanned within cooldown period
  var now = Date.now();
  if (decodedText === lastScannedCode && (now - lastScannedTime) < SCAN_COOLDOWN_MS) {
    // Same code scanned too quickly - ignore silently
    return;
  }
  
  // Update last scanned tracking
  lastScannedCode = decodedText;
  lastScannedTime = now;
  
  isProcessingScan = true;
  // ... rest of scan processing
}
```

### 2. Cooldown Reset on Mode Toggle
When the user toggles between IN/OUT mode, the cooldown is reset to allow immediate scanning:

```javascript
function setScanMode(mode) {
  currentScanMode = (mode === 'OUT') ? 'OUT' : 'IN';
  localStorage.setItem('event_scan_mode', currentScanMode);
  
  // Reset scan cooldown when mode changes (allow immediate scan after toggle)
  lastScannedCode = null;
  lastScannedTime = 0;
  
  // ... rest of mode toggle logic
}
```

## How It Works

### Scenario 1: Same QR Code Scanned Repeatedly
1. Student scans QR code at 10:00:00
2. Scanner processes the scan, beeps once, saves to offline queue
3. QR code is still in view, scanner detects it again at 10:00:01
4. **Debounce check**: Same code within 3 seconds → **Ignored silently**
5. Scanner continues detecting at 10:00:02 → **Ignored**
6. At 10:00:03+ → Cooldown expired, would allow scan if still in view

### Scenario 2: Different Students
1. Student A scans at 10:00:00 → Processed
2. Student B scans at 10:00:01 → **Different code** → Processed immediately
3. No cooldown between different QR codes

### Scenario 3: IN/OUT Toggle
1. Student scans IN at 10:00:00 → Processed
2. Guard toggles to OUT mode at 10:00:01
3. **Cooldown reset** → Student can scan OUT immediately
4. Same student scans OUT at 10:00:02 → Processed (no 3-second wait)

## Benefits

✅ **Single beep per scan** - No more multiple beeps for one QR code  
✅ **Clean offline queue** - No duplicate entries  
✅ **Better UX** - Clear feedback, no confusion  
✅ **Faster mode switching** - Immediate scan after IN/OUT toggle  
✅ **Silent ignore** - No error messages for repeated detections  

## Configuration

The cooldown period can be adjusted by changing the constant:

```javascript
var SCAN_COOLDOWN_MS = 3000; // Change to 2000 for 2 seconds, 5000 for 5 seconds, etc.
```

**Recommended values:**
- **3000ms (3 seconds)** - Default, good balance
- **2000ms (2 seconds)** - Faster for high-traffic gates
- **5000ms (5 seconds)** - More conservative, prevents accidental re-scans

## Testing

### Test 1: Offline Duplicate Prevention
1. Go offline (disconnect internet)
2. Scan a student QR code
3. Keep QR code in view for 5 seconds
4. **Expected**: Only 1 notification, 1 beep, 1 queue entry
5. **Before fix**: Multiple notifications, beeps, queue entries

### Test 2: Different Students
1. Go offline
2. Scan Student A → Should process
3. Immediately scan Student B → Should process
4. **Expected**: Both scans processed, no delay

### Test 3: Mode Toggle
1. Go offline
2. Scan Student A with IN mode → Should process
3. Toggle to OUT mode
4. Immediately scan Student A again → Should process
5. **Expected**: Both scans processed, no 3-second wait

### Test 4: Cooldown Expiry
1. Go offline
2. Scan Student A → Should process
3. Keep QR code in view
4. Wait 4 seconds
5. **Expected**: After 3 seconds, if QR still in view, would allow re-scan (but duplicate check in queue prevents it)

## Files Modified

- `templates/gate/gate_scan.html` (lines ~2564-2595)
  - Added debounce variables and logic in `onScanSuccess()`
  - Added cooldown reset in `setScanMode()`

## Related Features

This fix works together with:
- Offline queue duplicate detection (prevents same student from being queued twice)
- Event-aware duplicate checking (different events allow same student)
- Queue size limit (500 items max)

## Notes

- The debounce is **client-side only** and doesn't affect server-side duplicate detection
- The cooldown is **per-device** (stored in memory, not localStorage)
- Refreshing the page resets the cooldown
- The cooldown applies to **both online and offline modes** for consistency

---

**Status**: ✅ Implemented and tested  
**Date**: 2026-03-09  
**Impact**: High - Significantly improves offline scanning UX
