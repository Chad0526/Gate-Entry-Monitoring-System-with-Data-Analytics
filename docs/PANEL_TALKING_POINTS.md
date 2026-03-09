# Panel Talking Points — Top 3 to Stress

Use these when the panel asks “What’s strong about this system?” or “How is it production-ready?”

---

## 1. Analytics & reporting (faculty love this)

**One-liner:** *“Staff get live counts, CSV and Excel exports, and a printable attendance sheet, with quick search by student ID or name.”*

**What to show:**
- **Live dashboard** for an event: checked in / checked out / currently inside, auto-refresh every 5 seconds.
- **Attendance report** for an event: Export **Attendance (CSV)** and **Attendance (Excel)**; **Scan Logs (CSV)** and **Scan Logs (Excel)**.
- **Quick search** on the report: type a student ID or name, hit Search — table filters to that student.
- **Print:** “Print report” on the same page; “Currently inside” is also print-friendly.

**Why it matters:** Schools expect Excel and printable reports; live counts and search make it feel like a real operations tool.

---

## 2. Security & accountability (panel and IT care)

**One-liner:** *“Every scan is tied to a device and, when staff are logged in, to the user who recorded it; admins can void bad scans without deleting history.”*

**What to show:**
- **Device ID:** Scanner uses a stable UUID; it’s stored on every `AttendanceLog` row. “We can see which kiosk recorded which scan.”
- **Recorded by:** When a guard is logged in, `recorded_by` is set. Exports include “Recorded by” so you can answer “Who scanned this student?”
- **Void, don’t delete:** In Django Admin → Attendance logs, select rows → “Void selected logs”. Row stays for audit, excluded from reports and exports. “We correct mistakes without losing the audit trail.”
- **Attendance mode:** OPEN vs SECURE is enforced: SECURE events only accept token QR, not plain student ID.

**Why it matters:** Accountability (who did what, from which device) and safe corrections (void + retention) are standard expectations.

---

## 3. Usability for staff (real-world use)

**One-liner:** *“Staff can fix wrong scans and participation in admin, and students don’t need accounts — we’re a records and reporting system for the school.”*

**What to show:**
- **Corrections in admin:**  
  - Void a scan log (or unvoid).  
  - Mark attendance as present/absent.  
  - Edit `checked_in_at` / `checked_out_at` on an Event attendance row.
- **Deactivate student:** Admin → Students → uncheck “Is active”. No delete; history kept.
- **No student login:** Students are in the DB and have a QR; guards scan them. No student portal or passwords to manage.

**Why it matters:** Shows you thought about real events (mistakes, corrections) and scoped the system clearly (staff-only, records + reports).

---

## If they ask “What would you add next?”

- **Filter reports by date range** (e.g. scans between two dates).
- **SMS/email to staff** (e.g. “Event at 80% capacity”, “Scanner device offline”).
- **QR ID card batch print** (select students → generate printable page with QR + photo).

---

## One-sentence summary

*“We built a staff-only event attendance system with live counts, CSV and Excel exports, printable reports, quick search, full device and user audit trail, and safe data correction (void, mark present, edit timestamps) without losing history.”*

Use that as your closing line when they ask “So what did you deliver?”
