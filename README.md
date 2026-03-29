# City College of Bayawan – Gate Entry Monitoring & Data Analytics

**Django project:** `gate_analytics` · **App:** `gate` (Gate & Attendance Analytics)

Gate entry monitoring with data analytics. Students are identified via **QR code embedded on their ID cards** (QR encodes `student_id`). Flow: scan QR → retrieve profile → verify identity → grant or deny entry → record incident if denied → check event schedule → track attendance for active events → store data in campus analytics.

**Developed by:** NORSU-BSC Capstone Project

---

## System Flow (High Level)

```
Accounts: Admin / Faculty / Staff / Student Affairs (SAS for IDs & QR)
        ↓
Login & Role Check  (physical security staff do not use separate gate-only accounts)
        ↓
Dashboard  OR  Gate scan first (see below)
        ↓
Gate Scan / Event Management
        ↓
Database Logging (GateEntry, EventAttendance, GateIncident)
        ↓
Reports & Analytics
```

### Daily gate operations (recommended)

1. **Assigned staff** (e.g. SAS or rotating duty) opens the **gate PC** each morning and **logs in** with their account.
2. After login, **Staff / Faculty** are sent to **`/gate/`** (gate scanner) by default so the scan screen is ready immediately. **Admins** default to the dashboard (configurable in `gate_analytics/settings.py`: `LOGIN_REDIRECT_*`).
3. **Physical security** assists with crowd and safety only; they **do not use system accounts** (no separate “guard login”).
4. For a **full-screen, single-tab experience**, use **browser kiosk mode** (e.g. Chrome “Open as window” / `--kiosk`), **F11** fullscreen, or open **`/gate/?kiosk=1`** and use the **Fullscreen** button.

**Project structure & docs:** see **[docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)** and **[docs/CAPSTONE_PROJECT_STRUCTURE.md](docs/CAPSTONE_PROJECT_STRUCTURE.md)**.

---

## Role Access Table

| Area | Admin | Faculty | Staff | Student Affairs |
|------|:-----:|:-------:|:-----:|:---------------:|
| Dashboard | ✓ | ✓ | ✓ | ✓ |
| Events (create, list, categories, members) | ✓ | ✓ | ✓ | — |
| Gate scan, entries, analytics | ✓ | ✓ | ✓ | — |
| Students (list, create, edit, import CSV) | ✓ | ✓ | ✓ | ✓ |
| Django admin site | ✓ | — | — | — |

Roles are enforced via Django Groups (see `gate_analytics/roles.py`): **Admin**, **Faculty**, **Staff**, **Student**, **Student Affairs**. A legacy **Personnel** group may still appear in the database for older accounts; **staff/faculty** typically log in at the gate PC.

---

## Features (from flowchart)

- **Gate entry:** Student approaches gate → request ID (scan QR) → retrieve profile from database → verify identity.
- **Grant entry:** Record entry details; check event program schedule; if active event, track attendance (participated / non-participant).
- **Deny entry:** Deny gate entry, alert staff, record incident details (e.g. identity mismatch, invalid ID, not registered).
- **Campus analytics:** All gate entries, incidents, and event participation stored for reporting and administrative reports.

## Setup

### Linux / macOS
1. Clone: `git clone <repo-url>`
2. `cd django-event-management-master`
3. `python3 -m venv env` then `source env/bin/activate`
4. `pip install -r requirements.txt`
5. `python manage.py migrate`
6. `python manage.py createsuperuser`
7. `python manage.py runserver 8001` (or omit `8001` for default port 8000)

### Windows
1. Open project folder in terminal.
2. `python -m venv env` then `.\env\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py createsuperuser`
6. `python manage.py runserver 8001` (or omit `8001` for default port 8000)

### Access from other devices (LAN, phone, ngrok)

With **`DEBUG=True`** (default in `gate_analytics/settings.py`), **`ALLOWED_HOSTS`** is set to **`['*']`** so Django accepts any hostname (ngrok URL, local IP, etc.). You can override with **`DJANGO_ALLOWED_HOSTS`** in `.env` (comma-separated list).

To listen on **all network interfaces** (not only `127.0.0.1`), run:

- **Windows:** double-click **`runserver_global.bat`** or:  
  `python manage.py runserver 0.0.0.0:8000`
- **Linux/macOS:** `python manage.py runserver 0.0.0.0:8000`

Then open from another device using this PC’s **LAN IP** (e.g. `http://192.168.x.x:8000/`). **ngrok (same machine, after Django is running):** on Windows use **`ngrok-http-8000.bat`** or `ngrok http 127.0.0.1:8000` so the tunnel hits IPv4 and avoids **ERR_NGROK_8012** (see **[docs/NGROK_TUNNEL_CHECKLIST.md](docs/NGROK_TUNNEL_CHECKLIST.md)**). The first time, **Windows Firewall** may ask to allow Python on private networks—allow it for LAN access.

**Tunnel / ngrok:** localhost works but ngrok URL does not—see **[docs/NGROK_TUNNEL_CHECKLIST.md](docs/NGROK_TUNNEL_CHECKLIST.md)**. Test: **`verify-ngrok-tunnel.bat` `https://YOUR-SUBDOMAIN.ngrok-free.dev`** or PowerShell: **`.\scripts\verify-ngrok-tunnel.ps1 -Url "https://…"`** (must include `.\` path). **Free tier blank browser tab:** **[docs/NGROK_FREE_TIER_INTERSTITIAL.md](docs/NGROK_FREE_TIER_INTERSTITIAL.md)** and **`/ngrok-help/`**. **General:** **[docs/TROUBLESHOOTING_NGROK_LOGIN.md](docs/TROUBLESHOOTING_NGROK_LOGIN.md)**.

**Production / deployment:** run `python manage.py collectstatic` so CSS/JS (including CKEditor) are copied into `staticfiles/`. That folder is not kept in git; it is generated on each server. Use **`DEBUG=False`** and set **`DJANGO_ALLOWED_HOSTS`** to your real domain(s)—never rely on `*` in production.

## URLs

| URL | Description |
|-----|-------------|
| `/` | **Login page** (root) |
| `/login/` | Login (same as `/`) |
| `/dashboard/` | Dashboard (Admin defaults here; Staff/Faculty default to `/gate/` after login unless `?next=` is set) |
| `/gate/` | **Gate scan** – scan QR or enter student ID; add `?kiosk=1` for kiosk bar + fullscreen button |
| `/gate/?kiosk=1` | Same as above with kiosk helpers (still use OS/browser kiosk for true “no tabs”) |
| `/gate/save-scan/` | POST scan result (from scanner or manual entry) |
| `/gate/analytics/` | Campus analytics dashboard |
| `/gate/reports/today/` | **Today's gate report** (HTML + `?format=csv`) |
| `/gate/api/student-lookup/` | JSON student lookup (staff; used from scanner modal) |
| `/gate/students/` | List/add/edit students |
| `/gate/students/import-csv/` | Import students from CSV |
| `/gate/entries/` | Gate entry log |
| `/gate/incidents/` | Incidents (denied entries) |
| `/health/` | Health check (200 if app+DB up; 503 if DB down) |
| `/admin/` | Django admin (Admin role + Staff status) |
| `/gate/event-list/` etc. | Event program schedule (under `/gate/`; see `gate/urls.py`) |
| `/register/` | **Student registration** (self-service; pending admin approval) |
| `/gate/verify-face/` | POST face image for **2FA facial verification** (after QR scan) |

## Student registration

- Students can self-register at **/register/** (link from login: "Create account").
- Fields: First name, Last name, Email (required), Student ID (optional; if provided by school).
- If no Student ID is given, a temporary ID (e.g. `REG-XXXXXXXX`) is generated. Admin/registrar can edit and assign the official ID later.
- New registrations are created with **is_active=False** (pending approval). An admin/staff user must open **Gate → Students**, find the student, set **Active** to Yes and assign a proper Student ID if needed.

## Two-factor authentication (facial recognition)

- **Flow:** After a successful QR scan at the gate, staff (or the student) can optionally use **Verify face (2FA)** in the popup: click the button → allow camera → capture → the captured face is compared to the student’s enrolled photo on file.
- **Enrollment:** The student’s reference photo is the **Photo** field on their profile. Admin/staff set it when creating or editing a student (**Gate → Students**).
- **Backend:** The `/gate/verify-face/` API accepts `student_id` and `image` (file or base64). If the Python library **face_recognition** is installed (`pip install face_recognition`; requires **dlib**), the server performs real face matching. If not installed, the API returns a stub success so the flow can be tested; install **face_recognition** for production 2FA.
- **Optional dependency:** `pip install face_recognition` (and system dependency for dlib if needed).

## Student ID & QR code

- Each **student** has a unique `student_id` (e.g. `2024-001`). This value is **embedded in the QR code** on the student ID card.
- At the gate: scan the QR (or type `student_id` manually) → system looks up the student → staff verify identity → Grant or Deny.
- To generate QR codes for ID cards: use any QR generator and encode the `student_id` string (e.g. `https://yoursite.com/gate/?id=2024-001` or plain `2024-001`). The gate scan page accepts the ID in the lookup field.

## Backups & health

- **Database backup:** `python manage.py backup_db` (writes to `backups/db_YYYYMMDD_HHMMSS.sqlite3` or `.sql` for MySQL). Add `--with-media` to also pack `MEDIA_ROOT` into `backups/media_*.tar.gz`.
- **Scheduled backups (recommended):** Run daily via cron (Linux/macOS) or Task Scheduler (Windows), e.g. `0 2 * * * cd /path/to/project && . env/bin/activate && python manage.py backup_db --with-media`.
- **Health check:** `GET /health/` returns `200 OK` if the app and database are up, or `503` if the DB is unavailable (for load balancers or monitoring).

## Quick test

1. Open **http://127.0.0.1:8001/** (or **http://127.0.0.1:8000/** if using default port) to see the login page.
2. Log in, then go to **Gate → Students** and add a student (e.g. student_id `TEST-001`, name, email).
3. Open **Gate scan** (`/gate/`), enter `TEST-001` and click Lookup.
4. Verify the profile and click **Grant entry** or **Deny entry** (if denied, incident is recorded and staff alerted).
5. View **Analytics** and **Gate entries** / **Incidents** for reports.

## Original preview

![event-management](https://user-images.githubusercontent.com/39632170/88448650-d641af80-ce61-11ea-85e1-dc256d1e8155.png)
