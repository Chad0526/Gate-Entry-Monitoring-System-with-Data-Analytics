# Core vs Extensions (for defense)

This document defines what is **core** (essential to the thesis/capstone scope) vs **extensions** (optional or extended features) for the Gate Analytics / event management system. Use it to scope the defense and manuscript.

---

## Core (essential)

These are required for the system to fulfill its primary purpose: gate attendance, identity verification, deny handling, and basic analytics.

| Area | Feature | Notes |
|------|---------|--------|
| **Gate** | Gate scan (QR / student ID) | Primary entry point: scan → lookup student → grant or deny. |
| **Gate** | Grant / deny decision | Based on student active status and (if used) load slip/schedule. |
| **Gate** | Incident on deny | Deny for *not registered* or *inactive/pending approval* creates a `GateIncident`; attempts appear in gate incidents. |
| **Gate** | Gate entries list | Filterable list of scans; tab for incidents. |
| **Gate** | Gate incidents list | Filter by date/reason; audit trail for denied attempts. |
| **Identity** | Student record + QR | Student model, QR code generation, link to gate/event scans. |
| **Roles** | Role-based access | Admin, staff, guard, (student) with appropriate permissions. |
| **Analytics** | Main dashboard | `/dashboard/` – today’s granted/denied/incidents, event schedule. |
| **Analytics** | Campus Analytics dashboard | `/gate/analytics/` – campus analytics, School Performance charts, entries/incidents/visitors. |
| **Analytics** | Reports hub | `/gate/reports/` – real-time today, device status, links to reports. |
| **Data** | Data privacy & retention | Documented in `DATA_RETENTION_AND_PRIVACY.md`; manuscript summary included. |

**In short:** Core = scan → grant/deny → incident on deny → entries/incidents lists → three analytics dashboards → roles and privacy documentation.

---

## Extensions (optional / extended)

These add value but are not required to demonstrate the core contribution. They can be cited as “implemented extensions” or “future work.”

| Area | Feature | Notes |
|------|---------|--------|
| **Schedule** | Load slip / schedule import | CSV upload; used to allow/deny by schedule; import errors + optional CSV download. |
| **Gate** | Early-out reason | Optional reason when recording OUT (e.g. early dismissal). |
| **Events** | Event tracking | Event creation, categories, registration, check-in/out, participation, capacity. |
| **Visitors** | Visitor passes | Time-limited pass (e.g. VISITOR-xxx) scanned at gate; visitor log. |
| **Notifications** | Alerts | Denied-entry email, capacity alert, daily digest (cron). |
| **Reporting** | Printable report | `/gate/analytics/report/` – same data as Campus Analytics, print layout. |
| **Reporting** | Generated reports | Daily/weekly/monthly generated reports; compare events. |
| **Data** | Student import/export | Bulk import/export of students (e.g. CSV). |
| **UX** | Theming | Site name, logo, primary color (Admin → Site theme). |
| **Audit** | Audit log | Who did what, when (void, mark present/absent, etc.). |
| **Other** | Calendar .ics | Public calendar of events. |
| **Other** | Recurring events | Templates + management command to generate occurrences. |
| **Other** | Backup command | `backup_db` for SQLite/PostgreSQL. |
| **Other** | IP allowlist | Optional middleware to restrict admin/login by IP. |

---

## For the defense

- **Core:** Defend the design and implementation of gate scan, grant/deny, incident-on-deny, entries/incidents lists, the three analytics dashboards, roles, and data privacy/retention. This is the minimal viable system that meets the stated objectives.
- **Extensions:** Present as “implemented extensions” or “additional features”; if time is short, summarize in a table and focus the defense on core.
- **Manuscript:** Clearly label “core” and “extensions” (or “optional features”) in the methodology and results so the scope is unambiguous.
