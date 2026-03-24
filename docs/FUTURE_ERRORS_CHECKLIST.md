# Future Errors Checklist – System Audit

This document lists potential failure points and mitigations so you can avoid or fix them before they cause production errors.

---

## 1. Settings & environment

| Risk | Location | Mitigation |
|------|----------|------------|
| **DEBUG = True in production** | `gate_analytics/settings.py` | For production, set `DEBUG=False` (or read from env: `DEBUG=os.environ.get('DEBUG', 'false').lower() == 'true'`). Use a separate `settings_prod.py` or env-based switch. |
| **Hardcoded SECRET_KEY** | `gate_analytics/settings.py` | Always set `DJANGO_SECRET_KEY` in `.env` in production; remove or avoid relying on the fallback key. |
| **Missing .env** | Project root | App still runs with SQLite if `DB_ENGINE` is unset; ensure `.env` exists when using MySQL/PostgreSQL and that `DB_PASSWORD` is set. |
| **PostgreSQL TIME_ZONE** | `gate_analytics/settings.py` | For PostgreSQL, `TIME_ZONE`: None in DATABASES and `options`: `-c timezone=UTC` are required. Do not remove them or login will raise "database connection isn't set to UTC". |

---

## 2. Database

| Risk | Location | Mitigation |
|------|----------|------------|
| **Unapplied migrations** | Any app | Run `python manage.py migrate` after pull or before first run. If the server warns "unapplied migration(s)", apply them. |
| **PostgreSQL password** | `.env` | If you see "password authentication failed" or "no password supplied", set `DB_PASSWORD` in `.env` to the exact password for `DB_USER`. |
| **MySQL not running** | XAMPP / system | If using MySQL, ensure the service is started (e.g. XAMPP Control Panel). Use `python manage.py check_db` to verify. |
| **SQLite lock under concurrency** | SQLite | For multiple guards scanning at once, prefer PostgreSQL (or MySQL). See `docs/POSTGRESQL_SWITCH_GUIDE.md`. |

---

## 3. Views and `.get()` / `.first()` usage

Several views use `Model.objects.get(...)` without `get_object_or_404` or try/except. If the object is missing, Django raises `DoesNotExist` and returns 500 unless the view catches it.

| File | Approx. line / pattern | Mitigation |
|------|-------------------------|------------|
| `gate/gate_views.py` | Various `Student.objects.get(...)`, `Event.objects.get(...)` | Many already wrapped in `try/except Model.DoesNotExist`; any new `.get()` on user/URL input should use `get_object_or_404` or try/except and return 404/400. |
| `gate/gate_personnel_views.py` | `GateShift.objects.get(...)`, `User.objects.get(...)` | Ensure caller only hits these when the object is expected to exist (e.g. after checking `.exists()`), or wrap in try/except and return a proper response. |
| `gate/gate_personnel_services.py` | `GateNotification.objects.get`, `GateHandoverNote.objects.get`, `Student.objects.get` | These are used in controlled paths; `get_currently_inside_count` was updated to catch `GateEntry.DoesNotExist`. For others, add try/except if they can be called with invalid IDs. |

**Recommendation:** For any new view that fetches a single object by ID/slug from the URL or request, use `get_object_or_404(Model, pk=...)` so users get a 404 page instead of 500.

---

## 4. Context processors

| Risk | Location | Mitigation |
|------|----------|------------|
| **DB/query failure in every request** | `gate_analytics/context_processors.py` | `notifications_context` and `gate_notifications_context` are wrapped in try/except; on DB or query failure they return safe defaults (empty lists, zero counts) so the site does not 500 on every request. |
| **theme_context** | Same file | Already wrapped in try/except; returns default theme if anything fails. |

---

## 5. Middleware

| Risk | Location | Mitigation |
|------|----------|------------|
| **BlockedIPMiddleware** | `gate_analytics/middleware.py` | On refresh it queries `BlockedIP`; if the DB is down, every request can 500. Consider try/except around the query and treat failures as "no block list" so the site stays up. |
| **GateEntryMySQLFixMiddleware** | Same file | No-op for PostgreSQL/SQLite; only runs for MySQL. Safe. |

---

## 6. Management commands and background jobs

| Risk | Location | Mitigation |
|------|----------|------------|
| **backup_db** | `gate/management/commands/backup_db.py` | PostgreSQL: requires `pg_dump` on PATH and correct `DB_PASSWORD`. MySQL: requires `mysqldump`. Run manually once to verify; for cron, ensure env (e.g. `.env`) is loaded. |
| **generate_daily_report / generate_weekly_report** | `gate/management/commands/` | Depend on DB and time bounds; ensure migrations are applied and date logic matches your timezone. |
| **check_db** | `gate/management/commands/check_db.py` | Safe; use to verify DB connectivity (SQLite, MySQL, PostgreSQL). |

---

## 7. File and CSV/Excel import

| Risk | Location | Mitigation |
|------|----------|------------|
| **Empty or malformed student CSV** | `gate_views.import_students_csv` | Validate file and columns; show errors in-template. |

---

## 8. Static and media files

| Risk | Location | Mitigation |
|------|----------|------------|
| **Missing static files** | `static/` | Run `python manage.py collectstatic` when deploying; ensure `STATIC_ROOT` is served by the web server. |
| **Missing media** | `media/` | Ensure `MEDIA_ROOT` exists and is writable; serve at `MEDIA_URL` in production. |
| **404 on /favicon.ico** | Browsers | Optional: add a favicon or ignore; not a critical error. |

---

## 9. Security (production)

| Risk | Mitigation |
|------|------------|
| **DEBUG=True** | Set `DEBUG=False` and configure `ALLOWED_HOSTS` correctly. |
| **SECRET_KEY in code** | Use `DJANGO_SECRET_KEY` from environment only in production. |
| **.env in version control** | Keep `.env` out of git (e.g. in `.gitignore`); use `.env.example` as a template without secrets. |

---

## 10. Quick verification commands

Run these periodically or after changes:

```bash
# Database connection (SQLite / MySQL / PostgreSQL)
python manage.py check_db

# Unapplied migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate

# Static files (deploy)
python manage.py collectstatic --noinput
```

---

## Summary

- **Already mitigated:** PostgreSQL UTC (TIME_ZONE + options), gate_personnel_services `get_currently_inside_count` DoesNotExist, context processor theme_context, **notifications and gate_notifications context processors** (try/except with safe defaults), many gate_views using get_object_or_404 or DoesNotExist.
- **Watch out for:** DEBUG and SECRET_KEY in production, missing DB_PASSWORD for PostgreSQL/MySQL, any new `.get()` on user input without 404 handling, context processors and BlockedIPMiddleware when DB is down.
- **Optional improvements:** Wrap BlockedIPMiddleware in try/except for resilience when the DB is unavailable; use get_object_or_404 (or explicit 404/400) for every "get by ID from request" in new views.
