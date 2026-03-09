# Hybrid QR Event Attendance System

## System Overview

Your system now supports **TWO types of event attendance scanning**:

### 1. **Permanent Student QR** (Recommended for Most Events)
- Students use their **existing student ID QR codes** (already printed on ID cards)
- No need to generate new QR codes per event
- Perfect for: Founders Day, seminars, field trips, general assemblies, sports events
- Simpler logistics, faster deployment

### 2. **Event-Specific Token QR** (High-Security Events)
- Unique QR codes generated per student per event
- Token-based: `EVT:<event_id>:<unique_token>`
- Perfect for: Exams, competitions, ticketed events, VIP access
- Prevents QR sharing/copying, trackable, revocable

---

## How It Works

### Scanner Behavior

When a guard scans a QR code on the **Gate Scan** page:

1. **Event NOT selected** (dropdown is blank):
   - System processes as **daily gate entry** (existing behavior)
   - Logs to `GateEntry` table

2. **Event IS selected** (guard chooses event from dropdown):
   - System detects QR type:
     - **Student ID QR** (`2022-00123` or `STU:2022-00123`) → Uses permanent QR flow
     - **Token QR** (`EVT:15:abc123...`) → Uses token-based flow
   - Validates time window (event dates + 30min grace)
   - Checks for duplicates
   - Logs to `AttendanceLog` + marks `EventAttendance`

---

## For Regular Events (Permanent QR)

### Step 1: Create Event
Admin panel → Events → Add Event
- Name: "Founders Day 2026"
- Start date: 2026-02-20
- End date: 2026-02-20
- Save

### Step 2: Guard Scans
1. Open `/gate/` page
2. Select **"Founders Day 2026"** from event dropdown
3. Scan student's **permanent ID card QR**
4. System logs attendance automatically

### Step 3: View Attendance Report
Admin panel → Events → Find "Founders Day 2026" → Click **"Attendance Report"**

You'll see:
- Total scans
- Unique students checked in
- Duplicate attempts
- Invalid scans
- Detailed log with timestamps

---

## For High-Security Events (Token QR)

### Step 1: Create Event + Register Students
Admin panel → Events → Add Event
- Name: "Final Exam - CS101"
- Start date/end date
- Save

Then: Events → Find "Final Exam - CS101" → Click **"Manage Registrations"**

Options:
- **Register All Active Students** (bulk)
- **Import from CSV** (for specific list)
- **Manual registration** (one-by-one)

System generates unique tokens automatically.

### Step 2: Distribute QR Codes to Students
**Option A: Student Portal (Recommended)**
- Student logs in → "My Events" → Downloads their QR code
- *(You'll need to create this page)*

**Option B: Admin Bulk Print**
- Admin → Events → "Final Exam - CS101" → **"Print QR Codes"** → PDF with all students

**Option C: Send via Email**
- Export tokens to CSV → Send via email automation

### Step 3: Guard Scans Token QR
1. Open `/gate/` page
2. Select **"Final Exam - CS101"** from dropdown
3. Scan student's **event QR** (`EVT:...`)
4. System validates:
   - Token is valid
   - Not revoked
   - Correct event
   - Within time window
   - Not duplicate

### Step 4: View Attendance Report
Same as permanent QR method.

---

## Database Schema

### Key Models

#### `EventRegistration` (for token-based only)
- `event` (FK to Event)
- `student` (FK to Student)
- `token` (unique, 64-char)
- `status` (active/revoked)
- `checked_in_at`, `checked_out_at`

#### `AttendanceLog` (logs ALL scan attempts)
- `event`, `student`, `registration`
- `scan_time`, `client_scan_time` (for offline)
- `scan_type` (IN/OUT)
- `result` (SUCCESS/DUPLICATE/INVALID/REVOKED/WRONG_EVENT/OUTSIDE_WINDOW)
- `token`, `device_id`, `remarks`

#### `EventAttendance` (summary table)
- `event`, `student`
- `participated` (boolean)

---

## QR Code Formats Supported

| Format | Example | Use Case |
|--------|---------|----------|
| Plain student ID | `2022-00123` | Permanent QR (daily gate + events) |
| STU prefix | `STU:2022-00123` | Permanent QR (alternative format) |
| Event token | `EVT:15:Xw8m7pQy...` | Token-based event attendance |

---

## Duplicate Prevention

### For Permanent QR
Checks `AttendanceLog` for previous successful scans:
- **IN**: Allowed only if no prior IN or last scan was OUT
- **OUT**: Allowed only if last scan was IN

### For Token QR
Checks `EventRegistration` timestamps:
- **IN**: Allowed only if `checked_in_at` is NULL
- **OUT**: Allowed only if `checked_in_at` exists and `checked_out_at` is NULL

---

## Offline Support

Both QR types work offline:
1. Scanner stores scans in **IndexedDB** (local browser database)
2. When online, syncs to server automatically
3. Routes to correct endpoint based on `event_id` presence

---

## API Endpoints

### `POST /gate/scan-event/`
**For event attendance** (both permanent and token QR)

Request:
```json
{
  "event_id": 15,
  "qr": "2022-00123",  // or "EVT:15:token..."
  "scan_type": "IN",
  "device_id": "WEB-SCANNER",
  "client_scan_time": "2026-02-16T10:30:00+08:00"
}
```

Response (success):
```json
{
  "ok": true,
  "result": "SUCCESS",
  "message": "Juan Dela Cruz checked in successfully.",
  "color": "success",
  "scan_type": "IN",
  "time": "10:30 AM",
  "qr_type": "student_id",  // or "token"
  "student": {
    "student_id": "2022-00123",
    "name": "Juan Dela Cruz",
    "email": "...",
    "photo_url": "..."
  },
  "checked_in_at": "2026-02-16 10:30 AM",
  "checked_out_at": null
}
```

Response (duplicate):
```json
{
  "ok": false,
  "result": "DUPLICATE",
  "message": "Juan Dela Cruz already checked in at 09:15 AM.",
  "color": "warning",
  "student": {...},
  "checked_in_at": "2026-02-16 09:15 AM"
}
```

### `POST /gate/save-scan/`
**For daily gate entry** (no event selected)

Existing endpoint, unchanged.

---

## Testing the Hybrid System

### Test 1: Permanent QR Event Attendance

```bash
# Create test event
python manage.py shell
>>> from events.models import Event
>>> e = Event.objects.create(name="Test Seminar", start_date="2026-02-15", end_date="2026-02-16")
>>> e.id
15
>>> exit()

# Test scan with student ID QR
curl -X POST http://127.0.0.1:8000/gate/scan-event/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "event_id=15&qr=2022-00123&scan_type=IN&device_id=TEST"
```

### Test 2: Token-Based Event Attendance

```bash
python manage.py generate_event_test_token
# Follow the curl command printed by the script
```

---

## When to Use Which System

### Use Permanent QR When:
- ✅ Large open events (100+ attendees)
- ✅ Quick registration needed
- ✅ Students already have ID cards
- ✅ Security is not critical
- ✅ Simple logistics preferred

### Use Token QR When:
- ✅ Limited attendance (ticketed, reserved)
- ✅ Need to revoke access
- ✅ Prevent QR sharing/copying
- ✅ Audit trail required
- ✅ High-stakes events (exams, certifications)

---

## Admin Tasks

### Creating an Event (Either Type)
1. Admin panel → Events → Add Event
2. Fill in: Name, Description, Start/End dates, Venue
3. Save

### For Token-Based Events
4. Events → Find event → **"Manage Registrations"**
5. Choose registration method:
   - Register all active students
   - Import CSV (columns: student_id or email)
   - Manual add
6. System generates tokens automatically

### Revoking Access (Token-Based Only)
1. Events → Find event → "Manage Registrations"
2. Find student
3. Click "Revoke" → Status changes to "revoked"
4. Student's QR will be rejected at scanner

### Viewing Attendance
1. Events → Find event → **"Attendance Report"**
2. See:
   - Stats (total scans, unique students, duplicates)
   - Detailed log (all scan attempts with timestamps)
   - Export to CSV (for reports)

---

## Migration from Old System

If you had `EventAttendance` before:
- Keep it as summary table
- New `AttendanceLog` stores detailed scan history
- No breaking changes to existing data

---

## Security Considerations

### Permanent QR
- ⚠️ Student ID QRs can be photographed/shared
- ⚠️ No built-in anti-cheating
- ✅ Time window validation prevents wrong-day scans
- ✅ Duplicate prevention stops multiple check-ins

**Mitigation**: Show student photo on scanner result so guard can verify identity.

### Token QR
- ✅ Unique per student per event
- ✅ Cannot be reused across events
- ✅ Can be revoked if compromised
- ✅ Logged in detail (device, timestamp)

---

## Troubleshooting

### "Invalid QR code format"
- **Permanent QR**: Make sure QR contains student_id (e.g., `2022-00123`)
- **Token QR**: Make sure format is `EVT:<event_id>:<token>` (no spaces)

### "This QR code is for a different event"
- Token QR was generated for Event #10 but scanner has Event #15 selected
- Select correct event or re-generate QR

### "Outside event time window"
- Current time is not within event start/end dates (±30min grace)
- Check event dates, adjust if needed, or wait until event day

### "Already checked in"
- Duplicate scan detected
- This is expected behavior to prevent double-counting

### Offline scans not syncing
- Check browser console for errors
- Verify `/gate/scan-event/` endpoint is accessible
- Check IndexedDB in browser DevTools → Application → IndexedDB → GateOfflineDB

---

## Next Steps (Optional Enhancements)

### Phase 2: QR Distribution System
1. Student portal: "My Events" page
   - Lists registered events
   - Shows event QR codes
   - Download/print options

2. Admin bulk print:
   - PDF generator with all QR codes
   - Grid layout for ID cards

3. Email automation:
   - Send event QR via email
   - Reminder notifications

### Phase 3: Advanced Analytics
1. Attendance trends (by course, year level)
2. Late arrival tracking
3. Stay duration (check-in to check-out)
4. Export to Excel/CSV with filters

---

## Summary

You now have **maximum flexibility**:

- **Simple events** → Use permanent QR (students scan their ID cards)
- **Secure events** → Generate event tokens, distribute QR codes
- **Both work offline**, sync automatically
- **Full audit trail** in `AttendanceLog`
- **Admin tools** for registration + reporting

This is a **production-ready, capstone-worthy system** that balances simplicity and security.
