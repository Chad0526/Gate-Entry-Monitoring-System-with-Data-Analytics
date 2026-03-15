# Full System Structure – Capstone Project

**Project:** City College of Bayawan – Gate Entry Monitoring & Data Analytics  
**Type:** Capstone project (NORSU-BSC)  
**Stack:** Django, Python, Bootstrap, QR-based attendance, event management

---

## 1. Project Overview

A **campus gate entry and event attendance system** that:

- Identifies students via **QR codes** on ID cards (or manual ID entry).
- Records **IN/OUT** at the gate with policy-based allow/deny (schedule, lunch window, early out).
- Tracks **visitors** (reusable passes VIS-001 style or one-time) with check-in/check-out.
- Manages **events** (on-campus gate scan or field-trip scan) with **permanent student QR** or **token-based event QR**.
- Logs **incidents** (denied entry, proxy attendance).
- Provides **analytics**, **reports**, **audit log**, and **student/load-slip** management.

**Core flow:** Login → Role check → Dashboard / Gate scan → Scan or record entry → Database (GateEntry, EventAttendance, VisitorVisit, etc.) → Reports & analytics.

---

## 2. Technology Stack

| Layer        | Technology |
|-------------|------------|
| Backend     | Django 3.x, Python 3 |
| Database    | SQLite (default) or MySQL/PostgreSQL (env) |
| Frontend    | HTML/CSS/JS, Bootstrap 4, jQuery |
| QR          | python-qrcode, html5-qrcode (browser scanner) |
| Rich text   | CKEditor (event descriptions) |
| Optional    | face_recognition (2FA), Pillow (images), WeasyPrint (PDF reports) |

---

## 3. Project Directory Structure

```
django-event-management-master/
├── gate_analytics/              # Django project (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   ├── views.py                 # Login, dashboard, register, health, error pages
│   ├── middleware.py            # Session timeout, CSRF, gate scan short timeout
│   ├── roles.py                 # Admin/Faculty/Staff/Guard/Supervisor role checks
│   ├── context_processors.py    # Notifications, theme
│   └── notification_middleware.py
├── gate/                        # Main app: gate & attendance
│   ├── models.py                # All data models (see Section 5)
│   ├── gate_views.py            # Gate scan, save_scan, entries, students, visitors, events (gate), reports
│   ├── gate_urls.py             # /gate/* URLs (scan, save-scan, entries, students, etc.)
│   ├── urls.py                  # /gate/event-* (event list, categories, members, etc.)
│   ├── views.py                 # Event CRUD, categories, members, wishlist
│   ├── guard_views.py           # Guard dashboard, activity, notifications, performance, shift summary
│   ├── guard_services.py        # Guard notifications, activity logger, history, performance, realtime dashboard
│   ├── forms.py
│   ├── admin.py
│   ├── admin_notification_service.py
│   ├── policy.py                # Gate policy: IN/OUT allow/deny, lunch window, schedule, evaluate_scan
│   ├── audit.py                 # Audit logging helpers
│   ├── notifications.py
│   ├── utils.py
│   ├── services/                # import_loadslip, etc.
│   └── management/commands/     # backup_db, generate_daily_report, generate_weekly_report, generate_monthly_report, etc.
├── templates/
│   ├── base/                    # base.html, header, navbar, sidebar, footer, confirm_modal, login_base, js
│   ├── auth/                    # login.html, login_animated.html
│   ├── dashboard/               # dashboard.html
│   ├── errors/                  # 404.html, 500.html
│   ├── events/                  # event_list, create_event, edit_event, event_detail, event_category, etc.
│   ├── gate/                    # gate_scan, entry_list, student_list, visitor_*, event_*, guard_*, reports/, etc.
│   ├── legal/                   # privacy_policy.html, terms_and_conditions.html
│   ├── registration/            # student_register.html, student_register_animated.html, registration_animated.html
│   ├── users/                   # user_list.html
│   └── snippets/                # messages.html
├── static/                      # CSS (ccb-theme, dashboard-monitor), JS, images
├── media/
├── docs/                        # All .md documentation (see Section 9)
├── requirements.txt
├── manage.py
└── README.md
```

---

## 4. System Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User (Browser / Kiosk)                           │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Login / Register  │  Dashboard  │  Gate Scan  │  Events  │  Admin      │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Middleware: Session timeout, CSRF, Roles, Notifications                 │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Views: gate_views (scan, save_scan, record_entry, entries, students,    │
│         visitors, incidents, analytics, reports, visitor pass, etc.)     │
│  Views: guard_views (guard dashboard, activity, notifications, shift)   │
│  Views: event views (event CRUD, categories, members)                    │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Policy (policy.py): get_student_current_state, evaluate_scan          │
│  Services: guard_services (notifications, activity, performance),      │
│            load slip import, backup                                     │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Models: Student, GateEntry, GateIncident, Event, EventAttendance,       │
│          EventRegistration, VisitorPass, VisitorVisit, etc.              │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Database (SQLite / MySQL / PostgreSQL)                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Models (Summary)

### 5.1 Identity & access

| Model        | Purpose |
|-------------|---------|
| **Student** | Student profile: student_id (QR payload), name, photo, course/year/section, account_status (PENDING/APPROVED/REJECTED/INACTIVE), approved_by, load slips. |
| **StudentBlock** | Date-range block (or allowlist) for gate/event access. |
| **GatePolicy** | Single row: gate_open_time, lunch_out_start, lunch_in_start, general_out_until, strict_lunch_return, out_buffer_minutes. |

### 5.2 Gate & incidents

| Model         | Purpose |
|--------------|---------|
| **GateEntry** | One scan/record: student, event (optional), granted, incident (if denied), notes, scan_type (IN/OUT), result (SUCCESS/DENIED/DUPLICATE/…), out_reason, out_reason_code, timestamp, recorded_by. Indexes: timestamp, (granted, timestamp), (student, timestamp), (scan_type, timestamp). |
| **GateIncident** | Denied entry or proxy report: student, scanned_id, reason, details, timestamp. |

### 5.3 Events (programs)

| Model               | Purpose |
|--------------------|---------|
| **Event**          | Category, name, dates, status (draft/scheduled/active/completed/…), attendance_mode (OPEN/SECURE), event_location (on_campus/field_trip). |
| **EventCategory**  | Category for events. |
| **EventAttendance** | Per student per event: participated, checked_in_at, checked_out_at. |
| **EventRegistration** | Token-based: event, student, token (unique), status (active/revoked); check_in_at, check_out_at. |
| **AttendanceLog**   | Every event scan attempt: event, student, registration, scan_time, scan_type, result (SUCCESS/DUPLICATE/INVALID/…), token, device_id, recorded_by, voided. |

### 5.4 Visitors

| Model           | Purpose |
|----------------|---------|
| **VisitorPass** | Reusable (VIS-001) or one-time (VISITOR-xxx): code, status (AVAILABLE/IN_USE/DISABLED), current_visit, guest_name, department, valid_from/until, created_by. |
| **VisitorVisit** | One check-in/out: pass_obj, full_name, purpose, department, checked_in_at, checked_out_at, status (INSIDE/OUTSIDE). |
| **VisitorEntry** | Manual log: visitor_name, purpose, who_to_visit, recorded_by, timestamp, photo. |

### 5.5 Academic & schedule

| Model              | Purpose |
|-------------------|---------|
| **StudentLoadSlip** | Per student per semester: school_year, semester. |
| **LoadSlipSubject** | Subject rows: subject_code, schedule (e.g. TTH/ 10:00-11:30), day, start_time, end_time, room. Used by policy for IN/OUT windows. |

### 5.6 Other

| Model             | Purpose |
|------------------|---------|
| **AuditLog**     | user, action, model_name, object_id, description, ip_address, created_at. |
| **GeneratedReport** | report_type, period_start/end, title, summary (JSON), file, generated_by. |
| **ScannerDevice** | device_id (UUID), name, location, is_active, last_seen_at. |
| **NotificationRead** | user, notification_key (navbar “read” state). |
| **SiteTheme**    | site_name, logo, primary_color. |
| **EventMember**, **EventUserWishList**, **UserCoin**, **EventWaitlist**, **RecurringEventTemplate** | Legacy event-module models. |

### 5.7 Guard module

| Model             | Purpose |
|------------------|---------|
| **GuardShift**   | Guard clock-in/out: guard, gate_post, shift_start, shift_end. |
| **GuardNotification** | Notifications for guards: type (incident, capacity, shift_reminder, suspicious), priority, target_guard, related_incident/event, is_read. |
| **GuardActivityLog** | Audit of guard actions: scan, override, incident, shift_start/end, note, lookup; related_entry, related_shift, metadata (JSON). |
| **GuardNote**, **GuardNoteRead** | Shift handover notes and read state. |

---

## 6. Main URL Structure

### 6.1 Root / gate_analytics

| URL            | View / Purpose |
|----------------|----------------|
| `/`, `/login/` | Login |
| `/register/`   | Student self-registration (pending approval) |
| `/dashboard/`  | Dashboard (role-based) |
| `/logout/`     | Logout |
| `/health/`, `/ping/` | Health check (200/503) |
| `/users/`      | User list (admin) |
| `/privacy/`    | Privacy policy |
| `/admin/`      | Django admin |

### 6.2 Gate app (`/gate/`)

| URL | Purpose |
|-----|---------|
| `/gate/` | **Gate scan** (QR + manual ID, event dropdown, IN/OUT, visitor flow) |
| `/gate/save-scan/` | POST: process scan (student/visitor/event, policy, create GateEntry) |
| `/gate/scan-event/` | POST: event token/student scan (AttendanceLog, EventAttendance) |
| `/gate/record/` | POST: manual grant/deny entry (record_entry) |
| `/gate/record-early-out/` | POST: record OUT when already IN today |
| `/gate/lookup/` | GET: lookup student by ID |
| `/gate/register-student/` | Register student from scan (not found) |
| `/gate/visitor-checkin/`, `visitor-checkout/`, `visitor-force-checkout/`, `visitor-disable-pass/` | Visitor pass flow |
| `/gate/record-visitor/` | Manual visitor entry |
| `/gate/entries/` | Entry list (visits, event attendees, visitors, incidents by date) |
| `/gate/entries/event-attendees/` | Embed: event attendees for date |
| `/gate/students/` | Student list (approve, filter, search) |
| `/gate/students/create/`, `.../edit/`, `.../qr/` | Student CRUD, QR image |
| `/gate/students/import-csv/`, `.../export-csv/` | Import/export |
| `/gate/students/<pk>/load-slips/` | Load slip list/add/edit/export, upload CSV |
| `/gate/visitors/` | Visitor entry list |
| `/gate/incidents/` | Incident list; `/gate/incidents/report-proxy/` |
| `/gate/analytics/`, `/gate/analytics/report/` | Analytics dashboard & report |
| `/gate/guard-dashboard/` | Guard dashboard (redirect or guard/dashboard/) |
| `/gate/guard/dashboard/`, `guard/dashboard/stats/` | Guard dashboard view & stats API |
| `/gate/guard-activity/` | Guard activity (legacy) |
| `/gate/guard/activity-log/` | Guard activity log |
| `/gate/guard/notifications/`, `guard/performance/`, `guard/today-report/`, `guard/shift-summary/` | Guard notifications, performance, today report, shift summary |
| `/gate/visitor-pass/create/` | Create visitor passes (bulk slots or one-time) |
| `/gate/visitor-qr/print-all/` | Print all e-ID (HTML) or download ZIP of PNGs (?download=1) |
| `/gate/visitor-qr/<code>/` | QR image for pass |
| `/gate/visitor-qr/<code>/card/` | Single e-ID card (print) |
| `/gate/events/<id>/registrations/` | Event registrations (token QR) |
| `/gate/events/<id>/attendance-report/` | Attendance report (CSV/XLSX/PDF export) |
| `/gate/events/<id>/scan-logs/export-csv|export-xlsx/` | Scan logs export |
| `/gate/events/<id>/currently-inside/`, `live/`, `expected-today/`, `manual-checkin/`, `field-trip-scan/` | Event scan / field trip |
| `/gate/reports/`, `/gate/reports/list/`, `on-demand/`, `<pk>/download/` | Reports hub & download |
| `/gate/audit-log/` | Audit log viewer |
| `/gate/calendar.ics` | iCal export |
| `/gate/student-portal/` | Student portal |
| `/gate/api/attendance/`, `/gate/api/notification-count/` | Optional API (token) |

### 6.3 Events app (under `/gate/` via gate.urls)

| URL | Purpose |
|-----|---------|
| `/gate/event-list/`, `event-create/`, `detail/<pk>`, `event/<pk>/edit/`, `delete/<pk>` | Event CRUD |
| `/gate/category-list/`, `create-category/`, `category/<pk>/edit|delete/` | Event categories |
| `/gate/add-event-member/`, `join-event-list/`, `event-member/<pk>/remove/` | Event members |
| `/gate/event-wish-list/`, `add-event-wish-user/`, etc. | Wishlist, user mark, status |

---

## 7. Roles & Access

| Role      | Dashboard | Events (create/list) | Gate scan, entries, incidents, analytics | Students (list/create/edit/import) | Guard dashboard, activity | Admin site |
|-----------|-----------|----------------------|------------------------------------------|-------------------------------------|----------------------------|------------|
| Admin     | ✓         | ✓                    | ✓                                        | ✓                                    | ✓                          | ✓          |
| Supervisor| ✓         | ✓                    | ✓ (reports, export, audit)               | —                                    | ✓                          | —          |
| Faculty   | ✓         | ✓                    | —                                        | —                                    | —                          | —          |
| Staff     | ✓         | ✓                    | ✓                                        | ✓                                    | —                          | —          |
| Guard     | → Gate    | —                    | ✓                                        | —                                    | ✓ (own)                    | —          |

Enforced via `gate_analytics/roles.py` and `@role_required` decorator; groups: Admin, Supervisor, Faculty, Staff, Guard.

---

## 8. Key Features (Capstone-Relevant)

- **Gate scan:** QR or manual ID → lookup → policy (IN/OUT, lunch, schedule) → GateEntry; optional event selection; visitor pass (VIS-xxx) check-in/out. **Reason modal** is direction-aware: “Enter reason for entry” for IN scans (e.g. not in class yet), “Enter reason for early exit” for OUT scans.
- **Policy engine:** `policy.py` — get_student_current_state, evaluate_scan (IN/OUT, gate open, lunch window, class window, guard override).
- **Visit grouping:** `_gate_entries_to_visits` — group daily GateEntry by (student, local date), pair IN/OUT for display.
- **Event attendance:** OPEN (student QR) or SECURE (token QR); EventRegistration + AttendanceLog; field-trip scan (no GateEntry).
- **Visitor passes:** Reusable (VIS-001) or one-time; e-ID card (HTML + PNG); print all (4 per page, 3×4 in); download all as ZIP of PNGs (3×4 in at 96 DPI).
- **Students:** Approve/reject, load slip (CSV import), QR image, face photo for 2FA.
- **Reports & analytics:** Dashboard (cached counts), entry list by date, event attendance reports, export CSV/XLSX/PDF, on-demand and stored reports.
- **Audit:** AuditLog; role changes, incident creation, bulk import, void log, etc.
- **Infrastructure:** Session timeout (shorter for gate scan), health check, backups (DB + media), custom 404/500, indexes on high-volume tables.

---

## 9. Documentation Index (docs/)

| Document | Content |
|----------|---------|
| **CAPSTONE_PROJECT_STRUCTURE.md** | This document – full system structure, stack, URLs, roles, models. |
| **GATE_ENTRIES_STRUCTURE.md** | Full gate entry logic: GateEntry creation paths, policy, visit grouping, day bounds. |
| **HYBRID_QR_ATTENDANCE.md** | Permanent student QR vs token event QR; how to use each. |
| **PERMANENT_VS_TOKEN_QR.md** | Comparison, use cases, decision flow. |
| **DOCUMENTATION_INDEX.md** | Master index (testing, deployment, security). |
| **PRODUCTION_DEPLOYMENT_GUIDE.md** | Deployment, DB, Nginx, security. |
| **BACKUPS.md** | backup_db command, schedule, restore. |
| **EVENT_MODEL_STRUCTURE.md** | Event models and relationships. |
| **REPORT_GENERATION.md** | Report types and generation. |
| **FACE_PHOTO_AND_GATE_VERIFICATION.md** | 2FA face verification. |
| **STAFF_ACCESS_STUDENTS_SUGGESTIONS.md** | Staff role and student list access. |
| **EXTENDED_FEATURES.md**, **PROFESSIONAL_FEATURES.md** | Feature list. |
| **QUICK_TEST_GUIDE.md**, **VERIFICATION_CHECKLIST.md** | Testing and verification. |
| **FUTURE_ERRORS_CHECKLIST.md** | Potential failure points, mitigations, and quick verification commands. |

---

## 10. Setup & Run (Summary)

1. **Clone, venv, install:** `python -m venv env`, `pip install -r requirements.txt`
2. **Migrate:** `python manage.py migrate`
3. **Superuser:** `python manage.py createsuperuser`
4. **Run:** `python manage.py runserver` (e.g. 8000 or 8001)
5. **Optional:** `.env` for DB_ENGINE=mysql, SESSION_COOKIE_AGE, API_ATTENDANCE_TOKEN, NOTIFICATION_EMAILS, etc.
6. **Backup:** `python manage.py backup_db --with-media` (see docs/BACKUPS.md)

---

## 11. Capstone Deliverables Checklist

- **System overview** – This document + README + GATE_ENTRIES_STRUCTURE.
- **Architecture** – Section 4; modules: gate_analytics (auth, dashboard), gate (scan, entries, students, visitors, events, reports).
- **Data model** – Section 5; ER can be derived from `gate/models.py`.
- **Use cases** – Gate scan (student/visitor/event), record entry, early out, visitor check-in/out, event registration, reports, student approval.
- **Role matrix** – Section 7.
- **URL map** – Section 6.
- **Deployment** – docs/PRODUCTION_DEPLOYMENT_GUIDE.md, BACKUPS.md, health check.
- **Testing** – docs/QUICK_TEST_GUIDE.md, VERIFICATION_CHECKLIST.md.

---

*Generated for capstone project documentation. For implementation details, see `gate/models.py`, `gate/gate_views.py`, `gate/policy.py`, and the docs in `docs/`.*
