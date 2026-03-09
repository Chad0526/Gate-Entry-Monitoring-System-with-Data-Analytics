# Data Retention & Privacy

## What data is stored?

| Data | Purpose | Who can access |
|------|---------|----------------|
| **Student profile** (ID, name, email, photo, address, birthdate, guardians) | Identity and QR-based attendance | Admin, Staff (and Student for own record in portal) |
| **Gate entries** (timestamp, granted/denied, notes, recorded_by) | Daily campus IN/OUT audit | Admin, Staff |
| **Event attendance** (checked_in_at, checked_out_at, participated) | Event-level attendance and points | Admin, Staff; Student (own only) |
| **Attendance logs** (scan_time, result, device_id, token, remarks) | Full audit trail of every scan attempt | Admin, Staff |
| **Event registrations** (token, status, issued_at) | Secure event token issuance | Admin, Staff |
| **Scanner devices** (device_id, name, location, is_active) | Authorized scanner management | Admin |

---

## Who can access what?

- **Admin / Staff:** Full access to all data, reports, exports, and user/device management.
- **Guard:** Can scan at gate and at events; can view gate entries and incidents.
- **Student (portal):** Can view only their own gate logs and event attendance (when account is linked by student_id).
- **Faculty:** Event program schedule and related management (per your role setup).

---

## How long is data kept? (Retention policy)

- **Recommended retention:** Keep gate entries and attendance logs for **1–2 years** for audit and compliance; then archive or purge using the `purge_old_logs` management command.
- **Attendance logs:** Keep at least 1 year; then run `python manage.py purge_old_logs --older-than-months 24` (or your chosen period) to archive/delete older rows.
- **Gate entries:** Same as above or per school policy.
- **Student profiles:** Retain while enrolled; on leave/deactivation set `is_active=False` and keep record for compliance.
- **Event attendance / registrations:** Keep for the duration required by academic or event policy (e.g. semester, academic year).

---

## Deactivating a student

1. **Django Admin:** Events → Students → select student → uncheck **Is active** → Save.
2. Effect: Student can no longer be scanned for new events; existing gate and attendance records remain for audit.
3. Optional: Add an admin action “Deactivate selected students” for bulk deactivation.

---

## Archiving or deleting old logs

- **Management command (recommended):** Run `python manage.py purge_old_logs --older-than-months 24` to delete gate entries and attendance logs older than the specified months. Use `--dry-run` to preview. Use `--gate-only` or `--logs-only` to restrict to one model. Schedule monthly (e.g. via cron) to enforce retention.
- **Option B:** Use Django Admin filters and manual delete (only for small datasets).
- **Option C:** Use database-level partitioning or archiving (PostgreSQL) for large datasets.

---

## Security & access control

- **HTTPS:** Use encrypted connections in production (configure SSL at the server and set `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in production settings).
- **Database access:** Restrict database access to the application server; use strong credentials; do not expose the DB port publicly.
- **Application:** Role-based access (admin, staff, guard, faculty, student); CSRF protection; optional scanner device registration; no raw data exposed to unauthenticated users.

## Consent / policy page

- A **Privacy & data policy** page is available at **/privacy/** (public). It summarizes what data we collect, why, who can access it, retention, and how to request deactivation. Link it from the login page and student portal so students can read it before using the system.

## Privacy summary for panel

- **What we store:** Student identity data, gate and event scan timestamps, device IDs, and scan results.
- **Who can access:** Role-based (admin, staff, guard, student for own data).
- **Retention:** Configurable; recommend 1–2 years for logs, then archive/purge via `purge_old_logs`.
- **Deactivation:** Students can be deactivated (no new scans); history preserved for audit.
- **Security:** HTTPS in production, CSRF protection, optional device registration; no raw data exposed to unauthenticated users.

---

## For manuscript / defense: data privacy and retention

**Data collected**
- **Personal:** Student ID, name, email, photo, address, birthdate, guardians (for identity and QR-based gate/event attendance).
- **Operational:** Gate scan timestamps (IN/OUT), result (granted/denied), device ID, recorded-by user; event attendance (checked in/out, participated); visitor log (name, purpose, who to visit); incident records (denied/proxy with reason and details).

**Purpose**
- Gate and event attendance audit, campus analytics, and compliance with school policies. No data is used for purposes other than gate/attendance management and reporting unless stated in institutional policy.

**Access control**
- **Admin/Staff:** Full access to data, reports, and exports.
- **Guard:** Gate scan, view gate entries and incidents; no bulk export of PII.
- **Student (portal):** Own gate logs and event attendance only when account is linked by student_id.

**Retention**
- **Recommended:** Gate entries and attendance logs 1–2 years; then archive or purge via `purge_old_logs` (or equivalent). Student profiles retained while enrolled; on leave/deactivation, `is_active=False` with record kept for audit. Event attendance per academic/event policy (e.g. semester or academic year).

**Rights**
- Students can request deactivation (no new scans; existing records retained for audit). Privacy policy is available at `/privacy/` and can be linked from login and student portal.

**Security**
- HTTPS in production; CSRF protection; role-based access; database and app server locked down; no unauthenticated access to raw data.
