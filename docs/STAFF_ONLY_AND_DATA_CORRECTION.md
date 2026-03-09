# Staff-Only Scope & Data Correction

## Staff-only design

The system is built for **admin, staff, and guard** accounts only. There are **no student accounts** by design:

- Students are in the database (imported by registrar, or registered and approved).
- Student QR contains `student_id`; scanning does not require the student to log in.
- All reporting, exports, and corrections are done by staff.

**Benefits:**

- Simpler scope: no student login, password reset, or student-facing UI to maintain.
- Clear accountability: every scan and correction is tied to a staff user or device.
- Strong fit for a **records + reports** capstone.

---

## Device & audit trail

- **Stable device_id:** Each scanner uses a UUID in `localStorage` so you can tell which kiosk recorded which scan.
- **recorded_by:** Every event scan log (`AttendanceLog`) stores the logged-in user who was using the scanner (when available). Gate entries already had `recorded_by`.
- **Voided logs:** Admins can **void** a scan log (e.g. wrong scan, duplicate). The row stays for audit but is excluded from reports and exports.

So you can answer: *“Which guard scanned this student?”* and *“Was this log corrected/voided?”*.

---

## Data correction tools (admin)

Real events have mistakes. The system supports corrections without deleting history:

### 1. Void scan log

- **Where:** Django Admin → Attendance logs → select one or more → Action: **“Void selected logs”**.
- **Effect:** Sets `voided=True`, `voided_at=now`, `voided_by=request.user`. Voided logs are **excluded** from:
  - Attendance report “Recent scan logs”
  - Scan logs CSV/Excel export
  - Live dashboard “Recent scans”
- **Unvoid:** Action **“Unvoid selected logs”** to revert.

### 2. Mark as present / absent

- **Where:** Django Admin → Event attendances → select rows → Action: **“Mark selected as present”** or **“Mark selected as absent”**.
- **Effect:** Sets `participated=True` or `False` for the selected attendance rows. Use when you need to correct participation without re-scanning.

### 3. Edit attendance timestamps

- **Where:** Django Admin → Event attendances → open a record. You can edit `checked_in_at` and `checked_out_at` (and `participated`) when you need to fix IN/OUT times manually.

### 4. Deactivate student

- **Where:** Django Admin → Students → open student → uncheck **Is active** → Save.
- **Effect:** Student can no longer be scanned for new events; existing logs and attendances remain for audit.

---

## Exports and printable reports

- **CSV:** Attendance report and Scan logs (with **Recorded by** in scan logs).
- **Excel (.xlsx):** Same data as CSV; use “Attendance (Excel)” and “Scan Logs (Excel)” on the event attendance report page.
- **Print:** Attendance report and “Currently inside” pages are print-friendly (Print button / browser print).

---

## Attendance mode (OPEN / SECURE)

- **OPEN:** Any valid student QR is accepted for that event.
- **SECURE:** Only pre-registered token QR (`EVT:event_id:token`) is accepted; scanning a student ID returns an error.

This is enforced in the scan API so the system is “accurate” for both open and secure events.

---

## Privacy and retention

- See **DATA_RETENTION_AND_PRIVACY.md** for what is stored, who can access it, retention, and deactivation.
- **Deactivate student** instead of delete; **void** scan logs instead of deleting them, so the audit trail stays intact.

---

## Summary

| Need | How it’s covered |
|------|-------------------|
| Staff-only | No student login; guards/admins use the system |
| “Who scanned this?” | `recorded_by` on `AttendanceLog`; stable `device_id` |
| Fix wrong scan | Void log in admin; edit attendance timestamps; mark present/absent |
| Export for panel/school | CSV + Excel for attendance and scan logs |
| Printable | Print-friendly report and “Currently inside” |
| Audit trail | Voided logs kept with `voided_at` / `voided_by`; no row delete |
