# Extended Features Summary

This document lists optional and extended features: what’s implemented, what’s configured via settings, and what you can add next.

---

## Implemented

### Theming
- **SiteTheme** (Admin → Site theme): set site name, logo, primary color. Used in base template via `theme_context` (context processor). Ensure **theme_context** is in `TEMPLATES['OPTIONS']['context_processors']`.

### Audit log
- **Audit log viewer:** `/gate/audit-log/` (admin/staff). Lists who did what, when (void logs, mark present/absent, etc.). Also in Django Admin.

### Notifications & alerts
- **Denied entry:** Set `NOTIFY_ON_DENIED_ENTRY = True` in settings. Configure `ADMINS` or `NOTIFICATION_EMAILS` and `DEFAULT_FROM_EMAIL`. Email sent when gate entry is denied.
- **Capacity alert:** Set `NOTIFY_ON_CAPACITY_ALERT = True` (default). When event reaches 80% capacity, admin gets one email per event (`capacity_alert_sent_at` prevents repeats).
- **Daily digest:** Run `python manage.py send_daily_digest` (e.g. cron 8:00). Sends gate granted/denied and incident counts to admins.

### Visitor pass
- **Create pass:** `/gate/visitor-pass/create/` (admin/staff). Create a time-limited pass; code (e.g. VISITOR-xxx) is scanned at gate. Recent passes listed on same page.

### Calendar export
- **ICS:** `/gate/calendar.ics` – public .ics of scheduled/active events for Google Calendar / Outlook.

### Backup
- **Command:** `python manage.py backup_db [--output path]`. SQLite: copies DB file to `backups/` or given path. PostgreSQL: uses `pg_dump` if available.

### Recurring events
- **RecurringEventTemplate** in Admin: define weekly/monthly template. Run `python manage.py generate_recurring_events` to create next occurrence (uses first active EventCategory and first JobCategory). Use `--dry-run` to preview.

### Compare events
- **Report:** `/gate/reports/compare-events/?event_a=1&event_b=2` – side-by-side stats (registered, checked in, inside, capacity). Link from Reports hub.

### IP allowlist (optional)
- In settings, add `ALLOWED_ADMIN_IPS = ['1.2.3.4']` or `['10.0.0.0/8']`. Then uncomment `'gate_analytics.middleware.IPAllowlistMiddleware'` in `MIDDLEWARE`. Restricts `/admin/` and `/login/` to those IPs.

---

## Optional add-ons (not in codebase)

### 2FA (two-factor)
- Use **django-otp** + **django-two-factor-auth** (or similar). Add to `INSTALLED_APPS`, run migrations, protect admin or login with OTP. Document in your runbook.

### Webhook when report is generated
- In settings add `REPORT_WEBHOOK_URL` and optional `REPORT_WEBHOOK_HEADERS`. In management commands that create `GeneratedReport`, after save POST JSON (e.g. report id, type, period) to that URL. Implement when you need it.

### Incident photo
- **GateIncident** already has a `photo` field. In the incident report form (e.g. report proxy or guard incident flow), add `<input type="file" name="photo">` and in the view assign `request.FILES.get('photo')` to the incident before save.

### PWA (Progressive Web App)
- Add `manifest.json` (name, icons, start_url) and ensure the gate scan page is served over HTTPS. The existing `sw.js` (service worker) for gate scan can be extended. Link manifest in base template: `<link rel="manifest" href="/static/manifest.json">`.

### i18n (multi-language)
- Run `django-admin makemessages -l tl` (e.g. Filipino). Mark strings in templates with `{% trans %}` and in Python with `gettext`. Add `LANGUAGE_CODE` and `LANGUAGES` in settings. Use `LocaleMiddleware` and language prefix or cookie.

---

## Quick reference

| Feature            | Where / How |
|--------------------|-------------|
| Theming            | Admin → Site theme; base uses `site_name`, `site_primary_color`, `site_logo` |
| Audit log          | `/gate/audit-log/` or Admin → Audit logs |
| Denied alert       | `NOTIFY_ON_DENIED_ENTRY = True`, `ADMINS` / `NOTIFICATION_EMAILS` |
| Capacity alert     | `NOTIFY_ON_CAPACITY_ALERT = True` (default) |
| Daily digest       | `python manage.py send_daily_digest` |
| Visitor pass       | `/gate/visitor-pass/create/` |
| Calendar .ics      | `/gate/calendar.ics` |
| Backup             | `python manage.py backup_db` |
| Recurring events   | Admin → Recurring event templates; `python manage.py generate_recurring_events` |
| Compare events     | `/gate/reports/compare-events/` |
| IP allowlist       | `ALLOWED_ADMIN_IPS` + `IPAllowlistMiddleware` |
