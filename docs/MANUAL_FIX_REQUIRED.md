# MANUAL FIX REQUIRED - File Corruption Detected

## Problem

The automated edits I made corrupted the `templates/gate/gate_scan.html` file. The file needs to be manually fixed.

## Solution

You need to manually add ONE line of code to fix the offline scanning.

## Step-by-Step Fix

### 1. Open the File
Open `templates/gate/gate_scan.html` in your code editor (VS Code, Notepad++, etc.)

### 2. Find This Line (around line 4637)
Search for this text:
```javascript
var SCAN_COOLDOWN_MS = 1200;
```

### 3. Add This Line After It
Right after the line above, add this new line:
```javascript
var currentScanMode = 'IN';
```

### 4. The Result Should Look Like This
```javascript
var lastScannedCode = null;
var lastScannedTime = 0;
var SCAN_COOLDOWN_MS = 1200;
var currentScanMode = 'IN';  // ← ADD THIS LINE

function forceScannerReadyState() {
```

### 5. Save the File
Press Ctrl+S to save

### 6. Restart Django Server
1. Stop the server (Ctrl+C in terminal)
2. Start it again: `python manage.py runserver`

### 7. Test
1. Refresh browser (Ctrl+Shift+R)
2. Open Console (F12)
3. Type: `typeof currentScanMode`
4. Should show: `"string"` (not `"undefined"`)
5. Disconnect WiFi
6. Scan QR code
7. Should see success message

## Why This Fixes It

The variable `currentScanMode` was being used but never defined, causing JavaScript errors that prevented offline queue from working.

## Alternative: Use Git to Restore

If you have git, you can restore the file and apply the fix cleanly:

```bash
git checkout templates/gate/gate_scan.html
```

Then manually add the one line as described above.

## Need Help?

If you're not comfortable editing the file manually, let me know and I can guide you through it step by step.

