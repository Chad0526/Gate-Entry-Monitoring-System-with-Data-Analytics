# Daily Gate vs Event Popup - Complete Guide

## ROOT CAUSE IDENTIFIED

Looking at your screenshot, you're seeing the **DAILY GATE ENTRY popup** because:
1. ❌ **NO EVENT IS SELECTED** in the dropdown
2. ✅ You're scanning on daily gate entry (default mode)
3. ✅ The popup correctly shows "Based on class schedule: Classes not yet finished"

## Two Different Scenarios

### Scenario 1: DAILY GATE ENTRY (What you're seeing now)
**When**: No event selected in dropdown
**Popup**: Student info popup with class schedule messages
**Messages**: 
- "Based on class schedule: Classes not yet finished for the day"
- "Classes not yet finished for the day. Valid reason required for early exit (guard approval)"

### Scenario 2: EVENT ATTENDANCE (What you want to test)
**When**: Event IS selected in dropdown
**Popup**: Event early-out modal (orange theme)
**Messages**:
- "Leaving Event Early"
- "[Student Name] is leaving before the event ends"
- "Event: [Event Name]"
- "Event ends: [Time]"

## How to Test EVENT Early-Out Feature

### Step 1: Select an Event
```
1. Look at the top of the gate scan page
2. Find the yellow bar that says "Tracking event:"
3. Click the dropdown menu
4. Select an event (NOT "Daily Gate Entry (No event)")
```

### Step 2: Scan Student IN to Event
```
1. Make sure event is selected (you should see event name in yellow bar)
2. Scan student QR code
3. Select "IN" as scan type
4. Student checks in to the EVENT
```

### Step 3: Scan Student OUT Early
```
1. Keep the same event selected
2. Scan the SAME student QR code
3. Select "OUT" as scan type
4. NOW you should see the EVENT early-out modal (orange)
```

## Visual Differences

### Daily Gate Popup (Current Screenshot)
```
┌─────────────────────────────────────┐
│ ⚠️ Already scanned today           │ ← Yellow header
├─────────────────────────────────────┤
│ Maria Fe Acosta                     │
│ ID: 20240020                        │
│                                     │
│ ⚠️ Based on class schedule:        │ ← Class schedule message
│    Classes not yet finished...      │
│                                     │
│ Classes not yet finished for the    │
│ day. Valid reason required...       │
└─────────────────────────────────────┘
```

### Event Early-Out Modal (What you should see)
```
┌─────────────────────────────────────┐
│ 📅 Leaving Event Early             │ ← Orange header
├─────────────────────────────────────┤
│ ⚠️ Maria Fe Acosta is leaving      │
│    before the event ends.           │
│                                     │
│ Event: Basketball Tournament        │ ← Event name
│ Event ends: 05:00 PM               │ ← Event end time
│                                     │
│ Reason for leaving early *          │
│ ┌─────────────────────────────────┐ │
│ │ [Text area for reason]          │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Cancel] [Submit & Check Out]      │
└─────────────────────────────────────┘
```

## Troubleshooting Checklist

### ❌ Still seeing daily gate popup?
- [ ] Did you select an event from the dropdown?
- [ ] Is the event name showing in the yellow bar?
- [ ] Did you scan IN to the event first?
- [ ] Is the event end time in the future?

### ✅ How to verify event is selected:
1. Look for yellow bar at top of page
2. Should say "Tracking event: [Event Name]"
3. If it says "Daily Gate Entry (No event)" → No event selected!

## Backend Check

If event IS selected but still showing daily gate popup, check console:

```javascript
// Open browser console (F12) and type:
console.log('Selected Event ID:', selectedEventId);
// Should show a number, not null or undefined
```

## Database Check

Verify the scan went to the event table:

```python
python manage.py shell

from gate.models import EventAttendance, GateEntry
from django.utils import timezone

# Check if student is checked in to event
event_id = 1  # Replace with your event ID
student_id = "20240020"  # Replace with student ID

att = EventAttendance.objects.filter(
    event_id=event_id,
    student__student_id=student_id
).first()

if att:
    print(f"Checked in: {att.checked_in_at}")
    print(f"Checked out: {att.checked_out_at}")
    print(f"Early out reason: {att.early_out_reason}")
else:
    print("Student not checked in to this event")
```

## Summary

**Your screenshot shows DAILY GATE ENTRY popup (correct behavior)**
- No event selected = Daily gate mode
- Daily gate mode = Class schedule messages
- This is working as designed!

**To see EVENT early-out modal:**
1. SELECT AN EVENT from dropdown
2. Scan IN to event
3. Scan OUT before event ends
4. Event modal will appear (orange theme)

The two popups are completely separate and work correctly based on whether an event is selected or not!
