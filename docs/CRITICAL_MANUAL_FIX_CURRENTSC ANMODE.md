# CRITICAL MANUAL FIX REQUIRED - currentScanMode Variable

## Problem
The variable `currentScanMode` is used throughout the code but is NEVER DEFINED, causing `typeof currentScanMode` to return `'undefined'`. This breaks offline scanning completely.

## Root Cause
File corruption in `templates/gate/gate_scan.html` around lines 4640-4650. The automated editing tools cannot fix this due to the corruption.

## MANUAL FIX REQUIRED

### Step 1: Open the file
Open `templates/gate/gate_scan.html` in your text editor (VS Code, Notepad++, etc.)

### Step 2: Find the location
Search for this exact text (around line 4641):
```javascript
var SCAN_COOLDOWN_MS = 1200;
var scanProcessingStartedAt = 0;
```

### Step 3: Add ONE line
Add this line immediately after `var scanProcessingStartedAt = 0;`:
```javascript
var currentScanMode = 'IN';
```

### Step 4: The result should look like this:
```javascript
var SCAN_COOLDOWN_MS = 1200; // short cooldown to prevent duplicates without feeling unresponsive
var scanProcessingStartedAt = 0;
var currentScanMode = 'IN'; // <-- ADD THIS LINE

function forceScannerReadyState() {
```

### Step 5: Fix the corrupted function
The `forceScannerReadyState()` function is also corrupted. Find this:
```javascript
function forceScannerReadyState() {
  var statusIndicator = document.querySelector('.status-indicator');
  if (statusIndicator) {
    statusIndicator.classList.remove('scanning');
function processStudentId(qr_or_student_id, statusIndicator, eventIdAtScan) {
```

Replace it with:
```javascript
function forceScannerReadyState() {
  var statusIndicator = document.querySelector('.status-indicator');
  if (statusIndicator) {
    statusIndicator.classList.remove('scanning');
  }
}

function processStudentId(qr_or_student_id, statusIndicator, eventIdAtScan) {
```

### Step 6: Save the file

### Step 7: Restart Django server
```bash
# Stop the server (Ctrl+C in the terminal)
# Then restart it
python manage.py runserver
```

### Step 8: Clear service worker cache
In your browser console, run:
```javascript
navigator.serviceWorker.getRegistrations().then(function(registrations) {
  for(let registration of registrations) {
    registration.unregister();
  }
  location.reload(true);
});
```

### Step 9: Hard refresh
Press `Ctrl+Shift+R` to hard refresh the page

### Step 10: Verify the fix
In the browser console, type:
```javascript
typeof currentScanMode
```

It should return `"string"` (not `"undefined"`)

## Why Automated Tools Failed
The file has corruption where the `forceScannerReadyState()` function is missing its closing braces, causing the automated string replacement tools to fail pattern matching.

## After Manual Fix
Once you've manually added the line and verified `typeof currentScanMode` returns `"string"`, offline scanning should work:
1. Disconnect WiFi
2. Scan a QR code
3. You should see `[OFFLINE SCAN]` messages in console
4. You should see a green success message
5. The scan should appear in IndexedDB → GateOfflineDB → scans
