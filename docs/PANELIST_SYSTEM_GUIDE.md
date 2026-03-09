# Panelist Guide: System Models, APIs, and Functional Behavior

## 1. System Snapshot
- **Project name:** City College of Bayawan Gate Entry Monitoring and Data Analytics
- **Framework:** Django 3.x (server-rendered web app + selected JSON APIs)
- **Main app:** `gate`
- **Core purpose:** Control campus gate entry, track event attendance, manage visitor flow, and generate analytics/reports.

## 2. Tech Stack Used
- **Backend:** Django, Python
- **Database:** SQLite (default) or MySQL (via `.env`)
- **Forms/UI libraries:** `django-crispy-forms`, `django-betterforms`, CKEditor
- **Exports:** CSV, XLSX (`openpyxl`), PDF (`reportlab`, `weasyprint`, `playwright` fallback)
- **Image processing:** Pillow
- **Optional face processing during registration:** `face_recognition` (if installed)

## 3. Access Control and Roles
Roles are enforced via Django Groups in `gate_analytics/roles.py`:
- `Admin`
- `Supervisor`
- `Staff`
- `Faculty`
- `Guard`
- `Student` (legacy)

Behavior highlights:
- Users without role are blocked from normal app access.
- Guards are redirected to the Guard Dashboard after login.
- Admin/Staff/Supervisor have broader report/export/audit access.

## 4. High-Level System Behavior (What Happens in Real Use)
1. User logs in from `/` or `/login/`.
2. Guard scans student QR at `/gate/` (or does manual lookup).
3. System validates student status/policy/schedule and records IN/OUT decision.
4. If denied, incident is logged and visible in incident tracking.
5. Event attendance scans are logged separately for event analytics.
6. Dashboards and reports aggregate gate entries, incidents, attendance, and guard activity.

## 5. Core Data Models (What Each Part Stores)

### A. Event and Event Program Models
- `EventCategory`: Event grouping/category.
- `JobCategory`: Optional role/category for events.
- `Event`: Main event record (status, dates, audience targeting, attendance mode, venue, points/capacity).
- `EventImage`, `EventAgenda`: Extra event assets and schedule blocks.
- `EventMember`, `EventUserWishList`, `UserCoin`: Legacy event participation/wishlist/points features.
- `EventRegistration`: Per-student event registration token.
- `EventAttendance`: Event participation and check-in/check-out state.
- `AttendanceLog`: Detailed scan attempt history (success, duplicate, invalid, etc.).
- `EventWaitlist`: Waitlist for full events.
- `RecurringEventTemplate`: Auto-generation template for recurring events.

### B. Student and Academic Models
- `Student`: Main student identity/profile, approval status, course/year/section, photo, signature.
- `StudentLoadSlip`: Semester load-slip header per student.
- `LoadSlipSubject`: Subject schedule rows used for schedule-aware gate logic.
- `StudentBlock`: Temporary block/allow windows for access control.

### C. Gate and Incident Models
- `GateEntry`: Every gate scan result (IN/OUT, granted/denied, reason, scanner/audit info).
- `GateIncident`: Denied-entry incident details with reason and optional proof photo.
- `GatePolicy`: Time-based policy controls (gate open, lunch windows, out buffer rules).
- `ScannerDevice`: Registered scanner terminals and last-seen status.

### D. Guard Operations Models
- `GuardShift`: Clock-in/clock-out records per guard.
- `GuardNotification`: Notifications sent to guards.
- `GuardNote`: Shift handover notes.
- `GuardNoteRead`: Read acknowledgment for notes.
- `GuardActivityLog`: Immutable audit trail of guard actions.

### E. Visitor Management Models
- `VisitorPass`: Reusable/legacy visitor QR pass records.
- `VisitorVisit`: Visitor check-in/check-out lifecycle linked to pass.
- `VisitorEntry`: Manual visitor logbook entry.

### F. Reporting, Theme, and Audit Models
- `GeneratedReport`: Metadata/files for generated reports.
- `AuditLog`: Admin/staff action logs (login, updates, etc.).
- `AdminNotification`: Notifications for admin/staff users.
- `NotificationRead`: Per-user read state for notifications.
- `SiteTheme`: Site branding/theming settings.

## 6. Main URL Modules
- `gate_analytics/urls.py`
  - Auth pages, dashboard, health check, terms/privacy, includes gate modules.
- `gate/gate_urls.py`
  - Gate scan, visitor flows, guard dashboard, attendance scanner, reports, APIs.
- `gate/urls.py`
  - Legacy event management CRUD/workflows.

## 7. APIs and JSON Endpoints (Important for Panel Questions)
This system is mostly server-rendered, but has targeted API endpoints:

### Global/Auth Layer
- `GET /health/` and `GET /ping/`
  - Health/readiness check (`200` if app+DB available, `503` otherwise).
- `GET /dashboard/stats/`
  - Live dashboard metrics for admin/staff/faculty/supervisor view.

### Gate and Guard APIs
- `POST /gate/save-scan/`
  - Records scan workflow data from gate scanning UI.
- `POST /gate/scan-event/`
  - Event scan processing endpoint.
- `POST /gate/record-early-out/`
  - Records manual/override early OUT actions.
- `POST /gate/visitor-checkin/`, `POST /gate/visitor-checkout/`, `POST /gate/visitor-force-checkout/`
  - Visitor lifecycle APIs.
- `GET /gate/guard/dashboard/stats/`
  - Guard dashboard live stats JSON.
- `GET /gate/guard/notifications/check-new/`
  - Poll new guard notifications JSON.
- `GET /gate/api/notification-count/`
  - Navbar unread notification count JSON.
- `GET /gate/admin/notifications/check-new/`
  - Poll new admin notifications JSON.

### Integration API
- `GET /gate/api/attendance/`
  - Token-protected read-only integration endpoint.
  - Returns attendance and gate-entry aggregates plus sample rows.
  - Auth via `api_key` query param or `Authorization: Bearer <token>`.

## 8. Key Functionalities You Can Present
- QR-based student gate scanning with grant/deny outcomes.
- Schedule/policy-aware gate decision support.
- Incident recording for denied/proxy/invalid cases.
- Event attendance scanner with logs and exports.
- Student onboarding with pending approval workflow.
- Visitor QR pass management (check-in/check-out lifecycle).
- Guard shift management, notifications, and activity logging.
- Reports hub with daily/event/incidents/export flows.
- Audit and notification system for admin governance.

## 9. Suggested Panel Demo Flow (Fast and Clear)
1. Login as admin, show role-based dashboard stats.
2. Open `/gate/`, scan/lookup a student, show grant/deny result.
3. Show denied case creating a `GateIncident`.
4. Open event attendance scanner and show attendance logs.
5. Open visitor check-in/out to show reusable pass flow.
6. Open reports page and export sample CSV/XLSX/PDF.
7. Show guard activity/notifications for accountability.
8. Mention integration endpoint `/gate/api/attendance/` for external systems.

## 10. One-Line Architecture Summary for Defense
"The system is a Django-based, role-secured gate-and-attendance platform that unifies student entry control, event attendance, visitor tracking, and analytics reporting through a shared operational data model and focused JSON APIs."
