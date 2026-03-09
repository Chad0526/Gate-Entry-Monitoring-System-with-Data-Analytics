# Report Generation

## Overview

- **Real-time (Reports Hub):** Live occupancy, today’s entries, gate status, active scanner devices.
- **Daily (11:59 PM):** Entry summary by department/year level, peak times, denied scans list.
- **Weekly (Monday 7:00 AM):** Week-over-week trends, top peak hours, students with repeated anomalies.
- **Monthly (1st of month):** Executive summary, comparisons vs last month, scan success rate.
- **On-demand:** Admin picks date range; report by course/section, by student, by gate, or by time window (CSV/Excel/HTML).

## Prerequisites

- Run migrations so `Student` has `year_level` and `course_or_section`, and `GeneratedReport` exists:
  ```bash
  python manage.py migrate
  ```

## URLs (admin/staff)

- **Reports hub:** `/gate/reports/` — real-time dashboard and links to generated reports and on-demand.
- **Generated reports list:** `/gate/reports/list/` — list and download daily/weekly/monthly reports.
- **On-demand report:** `/gate/reports/on-demand/` — date range, group by, format (HTML/CSV/Excel).
- **Download report file:** `/gate/reports/<id>/download/`.

Navigation: sidebar **Reports** (Gate Access section) links to the hub.

## Scheduled reports (cron / Task Scheduler)

Run these at the recommended times:

| Report  | When        | Command |
|---------|-------------|--------|
| Daily   | 11:59 PM    | `python manage.py generate_daily_report` |
| Weekly  | Monday 7:00 AM | `python manage.py generate_weekly_report` |
| Monthly | 1st of month   | `python manage.py generate_monthly_report` |

Optional arguments:

- **Daily:** `--date YYYY-MM-DD` (default: yesterday). `--no-file` to skip CSV attachment.
- **Weekly:** `--week-ending YYYY-MM-DD` (Sunday of the week). `--no-file`.
- **Monthly:** `--month YYYY-MM`. `--no-file`.

Example (Linux cron):

```cron
59 23 * * * cd /path/to/project && python manage.py generate_daily_report
0 7 * * 1   cd /path/to/project && python manage.py generate_weekly_report
0 6 1 * *  cd /path/to/project && python manage.py generate_monthly_report
```

## Django admin

- **Generated reports** are in Django admin; list shows type, period, generated_at, generated_by, and whether a file is attached.
