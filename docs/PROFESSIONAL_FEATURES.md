# Professional Features: Privacy, Security, Health & Export

## 1) Data privacy & security

### Minimal data on guard screen
- **Guard dashboard** shows only **Student ID**, **time**, and **status** (Approved/Denied). Name is shown as **first name + last initial** (e.g. "Juan D.") to reduce exposure while still allowing guards to verify.
- **Scan result** messages can show first name only for "Welcome, [First name]" where implemented.
- Full names and contact details are available only to admin/staff in reports and admin, not on the guard kiosk list.

### Encrypted connection (HTTPS)
- **Production:** Use HTTPS only. In `settings_prod.py` (or your production settings):
  - `SECURE_SSL_REDIRECT = True`
  - `SESSION_COOKIE_SECURE = True`
  - `CSRF_COOKIE_SECURE = True`
- Configure SSL at the reverse proxy (e.g. Nginx, Caddy) or use a platform that provides TLS (e.g. Heroku, Railway).

### Database access control
- **Django:** Access is role-based (admin, staff, guard, faculty, student). Only admin/staff see full data exports and user management.
- **Database server:** Restrict DB access to the application server only; use strong passwords or IAM; avoid exposing the DB port publicly.
- **Backups:** Store backups in a secure location with restricted access.

### Retention policy (e.g. keep logs 1–2 years)
- **Recommended:** Keep gate entries and attendance logs for **1–2 years** for audit and compliance; then archive or purge.
- Configure the retention period in the management command **`purge_old_logs`** (see `docs/DATA_RETENTION_AND_PRIVACY.md`).
- Run it on a schedule (e.g. monthly):  
  `python manage.py purge_old_logs --older-than-months 24`

### Consent / policy page for students
- A **Privacy & data policy** page is available at **/privacy/** (public, no login).
- It summarizes what data is collected, why, who can access it, retention, and how to request deactivation.
- Link it from the login page footer and from the student portal so students can read it before using the system.

---

## 2) System health monitoring

### Scanner device status (online/offline, last sync)
- **Reports → Reports hub** shows **Scanner devices** with:
  - **Last seen** (last time a scan was recorded from that device).
  - **Status:** **Online** if last seen within the last 10 minutes; otherwise **Offline**.
- Event scan requests that send `device_id` update `ScannerDevice.last_seen_at` so status reflects recent activity.
- Use this to spot tablets that are off or disconnected.

### Daily backup
- **Option A:** Use your host’s backup (e.g. managed DB backups, VM snapshots).
- **Option B:** Run a daily backup script that:
  - Dumps the database (e.g. `pg_dump` for PostgreSQL, or copy SQLite file).
  - Stores the file in a secure, off-server location (e.g. S3, backup server).
- **Optional** management command: `python manage.py backup_db` can be added to dump the DB to a file and optionally upload elsewhere (document the command and schedule in your runbook).

### Error logs & admin notifications
- **LOGGING:** In production settings, configure `LOGGING` so errors go to files and/or to admin email (see Django docs: [Logging](https://docs.djangoproject.com/en/3.2/topics/logging/) and [Error reporting](https://docs.djangoproject.com/en/3.2/howto/error-reporting/)).
- **ADMINS:** Set `ADMINS` in settings so that when `DEBUG=False`, 500 errors are emailed to the listed addresses.
- **Optional:** Add a simple “Recent errors” view in Django admin (e.g. from a log table or reading from a log file) for quick checks.

---

## 3) Export & integration

### Export to PDF / Excel (admin reports)
- **Excel:** Event attendance report and scan logs already export to **.xlsx** (openpyxl). Generated reports (daily/weekly/monthly) can attach CSV/Excel.
- **PDF:** Event attendance report has a **Download PDF** button (reportlab). Install with `pip install reportlab`. Other reports can use the same pattern.

### Optional API for future attendance systems
- A **read-only API** is available at **GET /gate/api/attendance/**.
- **Query params:** `date_from`, `date_to` (YYYY-MM-DD; default last 7 days); `api_key=<token>` or header `Authorization: Bearer <token>`.
- **Enable:** Set environment variable `API_ATTENDANCE_TOKEN` (or `API_ATTENDANCE_TOKEN` in settings). If unset, the endpoint returns 401.
- **Response:** JSON with `date_from`, `date_to`, `gate_entries_count`, `event_scans_count`, `gate_entries_sample`, `event_scans_sample` (minimal fields; sample capped at 500 rows).

---

## Quick checklist

| Item | Status |
|------|--------|
| Minimal data on guard screen | ✅ Dashboard: ID + first name + last initial + time + status |
| HTTPS | ✅ Documented; enable in production settings & server |
| Database access control | ✅ Role-based in app; restrict DB server access |
| Retention policy (1–2 years) | ✅ Documented; `purge_old_logs` command |
| Consent / policy page | ✅ `/privacy/` |
| Scanner status (online/offline, last sync) | ✅ Reports hub |
| Daily backup | ✅ Documented; optional command |
| Error logs & admin notifications | ✅ Documented (LOGGING + ADMINS) |
| Export PDF/Excel | ✅ Excel in place; PDF optional |
| Optional API | ✅ Read-only attendance API |
