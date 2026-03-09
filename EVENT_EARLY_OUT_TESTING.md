# Event Early-Out Feature - Testing Guide

## What Was Fixed

The issue was that when scanning OUT from an event before it ends, the system was showing the **daily gate entry popup** with messages about "classes not yet finished" instead of the **event early-out modal**.

### Changes Made:

1. **Added console logging** to help debug the flow
2. **Added CSS styling** for the alert box in the event modal
3. **Verified the return statement** prevents the daily gate popup from showing

## How to Test

### Step 1: Setup
1. Make sure you have an active event (on-campus)
2. The event should be scheduled for today
3. The event end time should be in the future (e.g., if it's 2 PM now, event should end at 5 PM)

### Step 2: Scan IN to Event
1. Go to Gate Scan page
2. Select the event from the dropdown
3. Scan a student QR code with scan type "IN"
4. Student should check in successfully

### Step 3: Scan OUT Early (Before Event Ends)
1. Keep the same event selected
2. Scan the SAME student QR code with scan type "OUT"
3. **Expected Result**: Event early-out modal should appear (orange theme)
4. **Modal should show**:
   - "Leaving Event Early" header
   - Student name
   - Event name
   - Event end time
   - Textarea for reason
   - "Submit & Check Out" button

### Step 4: Verify Console Logs
Open browser console (F12) and look for these messages:
```
[EVENT EARLY OUT] Detected require_event_reason: {object}
[EVENT EARLY OUT] Modal shown
[EVENT EARLY OUT] Exiting early to prevent daily gate popup
```

### Step 5: Submit Reason
1. Enter a reason (minimum 5 characters)
2. Click "Submit & Check Out"
3. Student should check out successfully
4. Reason should be saved in database

## What Should NOT Happen

❌ **Daily gate popup should NOT appear** with messages like:
- "Based on class schedule: Classes not yet finished for the day"
- "Classes not yet finished for the day. Valid reason required for early exit (guard approval)"

❌ **Student info popup should NOT show** when require_event_reason is true

## Troubleshooting

### If daily gate popup still appears:

1. **Check browser console** for the log messages
2. **Hard refresh** the page (Ctrl+Shift+R) to clear cache
3. **Verify event is selected** in the dropdown before scanning
4. **Check backend response** in Network tab:
   - Look for the POST request to `/gate/scan-event-qr/`
   - Response should have `require_event_reason: true`
   - Response should have `result: "REQUIRE_EVENT_REASON"`

### If event modal doesn't appear:

1. Check console for JavaScript errors
2. Verify the modal HTML exists in the page (search for `eventEarlyOutModalOverlay`)
3. Check if `selectedEventId` variable has a value

## Database Verification

After submitting the early-out reason, verify it's saved:

```python
python manage.py shell

from gate.models import EventAttendance
from django.utils import timezone

# Get recent event attendance records
recent = EventAttendance.objects.filter(
    checked_out_at__isnull=False,
    early_out_reason__isnull=False
).order_by('-checked_out_at')[:5]

for att in recent:
    print(f"Student: {att.student.student_id}")
    print(f"Event: {att.event.name}")
    print(f"Checked out: {att.checked_out_at}")
    print(f"Reason: {att.early_out_reason}")
    print("---")
```

## Success Criteria

✅ Event early-out modal appears (orange theme)
✅ Modal shows event-specific information
✅ No daily gate popup appears
✅ Reason is saved to database
✅ Console logs show correct flow
✅ Student checks out successfully after submitting reason
