# Deep Check – Issues Found and Fixed

## 1. **Missing template (critical)**

- **Issue:** `event_manage_registrations` view rendered `gate/event_registrations.html`, but that template did not exist. Visiting any event’s “Registrations” page would raise **TemplateDoesNotExist** and a 500 error.
- **Fix:** Added `templates/gate/event_registrations.html` with:
  - Stats (total registered, checked in, checked out)
  - Form to “Register all active students”
  - Form to upload CSV (student_id column)
  - Table of registrations (student, token, status, issued, checked in/out)
  - Links back to attendance report and live dashboard

## 2. **Wrong Event status filter in notifications (upcoming events)**

- **Issue:** In `gate_analytics/context_processors.py`, “upcoming events” used:
  - `.exclude(status__in=('disabled', 'deleted', 'cancel'))`
  The **Event** model has `status` in `('draft', 'scheduled', 'active', 'completed', 'cancelled', 'archived')`. So `'disabled'`, `'deleted'`, and `'cancel'` never matched, and **cancelled/completed/draft/archived** events could still appear in the upcoming list.
- **Fix:** Replaced with:
  - `.filter(status__in=('scheduled', 'active'))`
  so only scheduled or active events in the date range are shown as upcoming.

## 3. **Verified (no change needed)**

- **Django check:** `python manage.py check` passes (0 issues). `check --deploy` reports only expected security warnings (DEBUG, SSL, HSTS, etc.) for development.
- **URLs:** All `{% url %}` names used in gate templates exist in `events/gate_urls.py`.
- **Views:** All views referenced in `gate_urls.py` exist in `gate_views.py`.
- **Templates:** Every `render(request, 'gate/...')` in `gate_views.py` now has a corresponding template (including the new `event_registrations.html`).
- **Audit / notifications:** `log_action` and `notify_denied_entry` / `notify_capacity_alert` are used correctly. `GateIncident.get_reason_display()` is valid (Django adds it for choices).
- **IP allowlist middleware:** Uses `django_settings.ALLOWED_ADMIN_IPS` (no typo).
- **Recurring events command:** Creates events only when an existing Event with the same category exists (to copy `location` for Mapbox `LocationField`). Failures are caught with try/except so one bad template does not stop the rest.

## 4. **Optional follow-ups (not bugs)**

- **Production:** When moving to production, address `manage.py check --deploy` warnings (SECURE_*, DEBUG=False, etc.), as in `PRODUCTION_DEPLOYMENT_GUIDE.md`.
- **Recurring events:** If `generate_recurring_events` fails for a template with “location” or similar, ensure at least one Event with that category exists so `location` can be copied.

---

**Summary:** One critical bug (missing `event_registrations.html`) and one logic bug (upcoming events filter) were fixed. The rest of the system check passed.
