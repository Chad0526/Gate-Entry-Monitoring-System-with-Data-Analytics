# Templates folder structure

Templates are grouped by feature so you can find and trace them easily.

## Folders

| Folder | Purpose | Main templates |
|--------|---------|----------------|
| **auth/** | Login & auth UI | `login.html`, `login_animated.html` |
| **base/** | Layout & shared pieces | `base.html`, `login_base.html`, `header.html`, `navbar.html`, `sidebar.html`, `footer.html`, `confirm_modal.html`, `js.html` |
| **dashboard/** | Main app dashboard | `dashboard.html` |
| **errors/** | Error pages | `404.html`, `500.html` |
| **events/** | Event management | `event_list.html`, `event_detail.html`, `create_event.html`, `edit_event.html`, `event_category.html`, etc. |
| **gate/** | Gate, scanning, personnel UI, reports | `gate_scan.html`, `entry_list.html`, `dashboard.html`, `gate_today_report.html`, `admin_send_gate_notification.html`, `pending_staff_guard.html`, `reports/` subfolder, etc. |
| **gate/reports/** | Report views | `overview.html`, `daily_gate.html`, `event_attendance.html`, `exports.html`, `_filter_bar.html`, `_reports_tabs.html` |
| **legal/** | Legal / policy pages | `privacy_policy.html`, `terms_and_conditions.html` |
| **registration/** | Student registration | `student_register.html`, `student_register_animated.html`, `registration_animated.html` |
| **snippets/** | Reusable fragments | `messages.html` |
| **users/** | User management | `user_list.html` |

## Where views point

- **gate_analytics/views.py** → `auth/login.html`, `dashboard/dashboard.html`, `users/user_list.html`, `errors/404.html`, `errors/500.html`, `legal/privacy_policy.html`, `legal/terms_and_conditions.html`
- **gate/views.py** → `events/*`
- **gate/gate_views.py** → `gate/*` and `gate/reports/*`
- **gate/gate_personnel_views.py** → JSON APIs under `/gate/api/...`, admin broadcast at `/gate/admin/broadcast-notification/`; template `gate/admin_send_gate_notification.html`

Use this file as a quick reference when tracing which HTML backs a URL or view.
