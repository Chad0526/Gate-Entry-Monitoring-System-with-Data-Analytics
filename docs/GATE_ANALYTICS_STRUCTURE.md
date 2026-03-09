# Gate Analytics – Full System Structure

How the **Gate & Attendance** and **Gate Analytics** system is organized and how it runs end-to-end.

---

## 1. High-level flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES (how data gets in)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Gate scan (QR/ID) → save_scan()     → GateEntry (granted=True/False)     │
│  • Manual deny/record → record_entry() → GateEntry + GateIncident           │
│  • Report proxy       → report_proxy_attendance() → GateIncident            │
│  • Scan deny (not registered / inactive) → save_scan() → GateIncident        │
│  • Visitor log        → record_visitor_entry()   → VisitorEntry             │
│  • Event QR scan      → scan_event_qr()          → AttendanceLog + optional  │
│                                                        GateEntry (event)    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE MODELS (gate app)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  GateEntry      – every gate scan (IN/OUT, granted/denied, timestamp, event)  │
│  GateIncident   – denied/reported incidents (reason, student, timestamp)       │
│  VisitorEntry   – manual visitor log (name, purpose, who_to_visit)            │
│  Student        – registered students (QR, load slip, account status)         │
│  EventAttendance – event participation (participated, checked in/out)        │
│  AttendanceLog  – event scan log (token/student QR at event)                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYTICS & REPORTING (read side)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Main dashboard (/dashboard/)           – today’s granted/denied/incidents  │
│  • Gate Analytics (/gate/analytics/)     – campus analytics + charts        │
│  • Gate entries list (/gate/entries/)     – filterable list + incidents tab  │
│  • Incidents list (/gate/incidents/)     – filter by date/reason             │
│  • Reports hub (/gate/reports/)          – real-time today + devices         │
│  • Printable report (/gate/analytics/report/) – same data, print layout      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Three analytics dashboards (for manuscript/defense):**

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| **Main dashboard** | `/dashboard/` | App home: today's granted/denied/incidents, event schedule; role-based (guard → gate-scan). |
| **Campus Analytics (Gate Analytics)** | `/gate/analytics/` | Full campus analytics: cards (granted, inside, denied, incidents, students, visitors), School Performance charts (monthly/annual), recent entries/incidents, visitors & departments, event participation. |
| **Reports hub** | `/gate/reports/` | Real-time today summary, device status, and links to generated reports (daily/weekly/monthly) and gate/incident lists. |

Print report: `/gate/analytics/report/` – same data as Campus Analytics in a printable layout.

---

## 2. URL structure (gate analytics and related)

| URL path | Name | View | Who |
|----------|------|------|-----|
| `/` | login | `login_page` | All |
| `/dashboard/` | dashboard | `gate_analytics.views.dashboard` | admin, faculty, staff (guard → redirect to gate-scan) |
| `/gate/` | gate-scan | `gate_views.gate_scan` | admin, staff, guard |
| `/gate/save-scan/` | save_scan | `gate_views.save_scan` | admin, staff, guard |
| `/gate/record/` | gate-record | `gate_views.record_entry` | admin, staff, guard |
| **`/gate/analytics/`** | **gate-analytics** | **`gate_views.analytics_dashboard`** | **admin, staff, guard** |
| **`/gate/analytics/report/`** | **gate-analytics-report** | **`gate_views.analytics_report`** | **admin, staff, guard** |
| `/gate/entries/` | gate-entry-list | `gate_views.entry_list` | admin, staff, guard |
| `/gate/incidents/` | gate-incident-list | `gate_views.incident_list` | admin, staff, guard |
| `/gate/incidents/report-proxy/` | gate-incident-report-proxy | `gate_views.report_proxy_attendance` | admin, staff, guard |
| `/gate/visitors/` | gate-visitor-list | `gate_views.visitor_entry_list` | admin, staff, guard |
| `/gate/students/` | gate-student-list | `gate_views.student_list` | admin, staff |
| `/gate/guard-dashboard/` | guard_dashboard | `gate_views.guard_dashboard` | guard |
| `/gate/reports/` | reports-hub | `gate_views.reports_hub` | admin, staff |

Root URL config: `gate_analytics/urls.py` → `path('gate/', include('gate.gate_urls'))` and `path('gate/', include('gate.urls'))` (events).

---

## 3. Gate Analytics pages in detail

### 3.1 Campus Analytics dashboard – `analytics_dashboard`  
**File:** `gate/gate_views.py`  
**Template:** `templates/gate/analytics.html`  
**URL:** `/gate/analytics/`  
**Query:** `?year=YYYY` (default: current year)

**Data computed (all use local day/month bounds for timezone correctness):**

- **Today**
  - `granted_today` – count of “visits” (IN+OUT grouped) via `_granted_visits_count_for_date(today)`
  - `denied_today` – `GateEntry` with `granted=False` in today’s local day
  - `incidents_today` – `GateIncident` in today’s local day
  - `total_students` – active students
  - `active_events` – events active/scheduled for today, on-campus
  - `recent_entries` / `recent_incidents` – latest 5 each

- **Selected year**
  - Monthly: `monthly_granted`, `monthly_denied`, `monthly_incidents` (12 months)
  - Incidents by reason: `reason_labels`, `reason_counts`, `reason_colors`
  - Annual: `annual_years`, `annual_granted`, `annual_denied`, `annual_inc` (last 6 years)

- **Visitors**
  - `visitors_this_month` – from start of month to end of today (local)
  - `visitors_this_year` – by `timestamp__year`
  - `top_departments_monthly` / `top_departments_annually` – by `who_to_visit`

- **Event participation**
  - `participation_stats` – per event: total, participated, non-participant

**Helpers used:**  
`_local_day_bounds(date)`, `_granted_visits_count_for_date(date)`, `_get_active_events()` (all in `gate_views.py`).

---

### 3.2 Printable analytics report – `analytics_report`  
**File:** `gate/gate_views.py`  
**Template:** `templates/gate/analytics_report.html`  
**URL:** `/gate/analytics/report/`

Same metrics as the dashboard (today + year + visitors + participation), with:
- `recent_entries` / `recent_incidents` limited to 50
- Layout suited for printing (no charts, summary + lists).

---

## 4. Where “today” and dates come from

- **Date used as “today”:** `timezone.localdate()` (app timezone from `settings.TIME_ZONE`).
- **Filtering “today”:** everywhere we use **local day bounds**:
  - `day_start`, `day_end = _local_day_bounds(today)`  
  - Queries: `timestamp__gte=day_start`, `timestamp__lt=day_end`  
  So dashboard, analytics, entries list, incidents list, guard dashboard, reports hub, policy (inside/outside), and daily digest email all share the same definition of “today” and avoid UTC vs local bugs.

---

## 5. Data flow into the system (what feeds analytics)

| Action | View / endpoint | Creates / updates |
|--------|------------------|-------------------|
| Scan QR/ID at gate (allow) | `save_scan` (POST) | `GateEntry` (granted=True, result=SUCCESS), optional `EventAttendance` |
| Scan QR/ID at gate (deny by policy) | `save_scan` (POST, allowed=False) | No entry; user can later “Record deny” |
| Manual “Record entry” (grant) | `record_entry` (POST) | `GateEntry` (granted=True) |
| Manual “Record entry” (deny) | `record_entry` (POST, granted=False) | `GateIncident` + `GateEntry` (granted=False, incident=…) |
| “Report proxy” on an entry | `report_proxy_attendance` (POST) | `GateIncident` (reason=proxy_attendance), linked to student |
| Log visitor | `record_visitor_entry` | `VisitorEntry` |
| Event QR scan | `scan_event_qr` | `AttendanceLog` (+ optional `GateEntry` with event set) |

Analytics and dashboard **read** from `GateEntry`, `GateIncident`, `VisitorEntry`, `EventAttendance`, and (for reports hub) `AttendanceLog`. They do not write these models.

---

## 6. Main models (relevant fields)

**GateEntry**  
- `student`, `event` (optional), `granted`, `incident` (optional), `notes`, `scan_type` (IN/OUT), `result`, `out_reason`, `out_reason_code`, `timestamp`, `recorded_by`

**GateIncident**
- `student` (optional), `scanned_id`, `reason` (identity_mismatch, invalid_id, not_registered, proxy_attendance, other), `details`, `timestamp`

**Incident on deny (not registered / unapproved):** When a gate scan is denied because the student is **not registered** or **inactive** (pending approval), `save_scan` creates a `GateIncident` (reason `not_registered` or `other` with details "student not active (pending approval)") so the attempt appears in **Gate incidents** and can be reviewed by guards/admins.

**VisitorEntry**  
- `visitor_name`, `purpose`, `who_to_visit`, `recorded_by`, `timestamp`

**Student**  
- `student_id`, name, photo, load slip (schedule), `account_status`, `is_active`, etc.

---

## 7. Roles and access

- **Roles:** Admin, Faculty, Staff, Guard, Student (Django groups; `gate_analytics.roles`).
- **Gate Analytics (Campus analytics):** `@role_required('admin', 'staff', 'guard')` – guards can view.
- **Dashboard:** Admin/faculty/staff see dashboard; guard is redirected to gate-scan.
- **Gate scan, entries, incidents, reports:** admin, staff, guard (and student only for student-portal).

---

## 8. Templates and UI

- **Base:** `templates/base/base.html`, `templates/base/sidebar.html`
- **Gate Analytics:** `templates/gate/analytics.html` (cards, charts, year selector, recent entries/incidents, visitors, participation)
- **Print report:** `templates/gate/analytics_report.html`
- **Related:** `templates/dashboard.html` (main dashboard with “today” counts and event schedule), `templates/gate/entry_list.html`, `templates/gate/incident_list.html`, `templates/gate/reports_hub.html`

Sidebar: “Campus analytics” links to `gate-analytics`; “Gate entries” and “Incidents” link to the lists that show the same underlying data by date.

---

## 9. Summary

- **Gate Analytics** = Campus analytics dashboard + printable report. They **read** from `GateEntry`, `GateIncident`, `VisitorEntry`, and event-related models.
- **Data gets in** via gate scan (`save_scan`), manual record (`record_entry`), report proxy (`report_proxy_attendance`), visitor log, and event scan.
- **“Today”** is consistent everywhere using `_local_day_bounds(today)` (and same idea in policy/notifications), so counts and lists stay in sync and timezone-safe.
- **Structure:** `gate_analytics` app (login, dashboard, roles, settings) + `gate` app (models, gate_views, gate_urls) + shared base templates and sidebar.
