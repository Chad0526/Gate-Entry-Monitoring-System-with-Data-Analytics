# Staff Access to Student Data – Suggestions

Quick reference for how staff/faculty access student-related features today, and what you could add or tighten.

---

## Current Access (Summary)

| Area | Admin | Staff | Faculty | Guard |
|------|-------|-------|---------|-------|
| **Student list** (view all, filter, pending) | ✅ | ❌ | ❌ | ❌ |
| **Student create / edit / approve** | ✅ | ❌ | ❌ | ❌ |
| **Student import/export CSV** | ✅ | ❌ | ❌ | ❌ |
| **Student portal** (own gate logs, events, points) | ✅ | ✅* | ❌ | ❌ |
| **Gate scan, entry list, visitors, incidents** | ✅ | ✅ | ❌ | ✅ |
| **Event attendance** (scanner, report, registrations) | ✅ | ✅ | ✅ | ✅ |
| **Reports** (overview, daily gate, exports, audit) | ✅ | ✅ | (some) | (limited) |
| **Guard dashboard, shift, notifications** | (supervisor) | (supervisor) | ❌ | ✅ |

\* Staff can open Student Portal, but it only shows data for the logged-in user (username = student_id). So staff see their own data if linked, or an empty view—they **cannot** look up another student’s portal.

---

## Suggestions

### 1. **Give staff (and optionally faculty) read‑only student list**

- **Why:** Office staff, registrars, or faculty often need to look up students (name, ID, course, year, status) without having full admin.
- **What:** Allow `staff` (and optionally `faculty`) to use the existing **Student list** page in **read‑only** mode:
  - View and filter by course, year, section, search by name/ID.
  - **No** “Approve all”, “Create student”, “Edit”, “Import/Export” for non‑admin (or hide those buttons/links by role).
- **How:** Add a decorator or view logic that allows `admin`, `staff` (and optionally `faculty`) for `student_list`, and in the template hide create/edit/approve/import/export for non‑admin. Optionally add a separate “Student list (read‑only)” URL if you want a distinct permission.

### 2. **Add a read‑only “Student detail” / look‑up view**

- **Why:** Staff/faculty need to answer “who is this student?” or “what’s their recent gate/event activity?” without seeing the full list or editing.
- **What:** A single **student detail** page showing:
  - Basic info: name, ID, course, year, section, status (approved/pending).
  - Last N gate entries and last N event attendances (same idea as student portal, but for any student that staff/faculty are allowed to see).
- **Who:** Allow `admin`, `staff`, and optionally `faculty`. Guards could get a “minimal” version (e.g. only when coming from a lookup) if you want.
- **How:** New view + URL, e.g. `gate/students/<pk>/` or `gate/students/lookup/?id=...`, with `@role_required('admin','staff','faculty')` and a simple template. Reuse the same queries as student portal (filter by `student_id` or `pk`).

### 3. **“View as student” (student portal on behalf of a student)**

- **Why:** Staff helping a student over the phone or at the counter need to see the same screen the student sees (gate logs, event attendance, points).
- **What:** From the student list or the new student detail, add an action like **“View portal”** that opens the **student portal for that student** (same content as when the student logs in).
- **Who:** Restrict to `admin` and `staff` (and optionally `faculty`). Log who viewed whose portal (audit).
- **How:** Either:
  - A dedicated URL like `gate/student-portal/<student_id>/` that loads that student’s data and renders the same portal template, with `@role_required('admin','staff')`, or
  - Reuse current `student_portal` with a GET param like `?as_student=<student_id>` when role is staff/admin, and log the access.

### 4. **Let staff (e.g. registrar) approve pending students**

- **Why:** Approving registrations is often an office/registrar task, not only for the tech admin.
- **What:** Allow `staff` (or a dedicated “Registrar” role if you add one) to:
  - See pending students (already possible if you give them read‑only list as in (1)).
  - Approve one student, or “Approve all” pending.
- **How:** Change `approve_all_pending_students` and the single‑student approve action (if any) to `@role_required('admin','staff')`. Optionally restrict “Approve all” to admin only and keep single approval for staff.

### 5. **Audit who viewed student data**

- **Why:** Compliance and accountability when staff/faculty view student records.
- **What:** Log each access to:
  - Student list (optional, can be noisy),
  - Student detail,
  - “View as student” portal.
- **How:** Use your existing `AuditLog` (or similar): on each of those views, log something like `action='student_record_view'`, `object_id=student.pk`, `user=request.user`, and optionally `extra={'view':'list'|'detail'|'portal'}`.

### 6. **Optional: scope staff/faculty by course or department**

- **Why:** Limit staff or faculty to “only students in my course/department.”
- **What:** If you have a “course” or “department” on the User profile (or a separate StaffProfile), filter the student list and student detail so staff/faculty only see students in that course/department. Admin sees all.
- **How:** Add a field to the user (or profile), e.g. `assigned_course` or `department`, and in the student list/detail queryset do something like `Student.objects.filter(...).filter(course=request.user.staffprofile.assigned_course)` when role is staff/faculty.

### 7. **Keep student create/edit and bulk import/export as admin‑only**

- **Recommendation:** Leave **create**, **edit**, **import**, and **export** of students as **admin only**. Broader “view” and “approve” can go to staff; structural changes (new students, bulk data) stay with admin.

---

## Suggested order of implementation

1. **Read‑only student list for staff** (and optionally faculty) + hide create/edit/approve/import/export for non‑admin.
2. **Student detail (read‑only)** for admin/staff/faculty.
3. **“View portal” for a chosen student** for admin/staff, with audit log.
4. **Staff can approve** pending students (single and/or “Approve all”).
5. **Audit log** for student record views (detail + portal).
6. (Optional) **Scope by course/department** for staff/faculty.

---

## Quick reference: where to change in code

- **Roles:** `gate_analytics/roles.py` — `get_user_role`, `role_required`, `ROLE_NAMES`.
- **Student list:** `gate/gate_views.py` — `student_list` (decorator + template links).
- **Student approve:** `gate/gate_views.py` — `approve_all_pending_students` and any single-approve view.
- **Student portal:** `gate/gate_views.py` — `student_portal` (optional `?as_student=` or new URL).
- **New student detail view:** new view in `gate/gate_views.py`, new URL in `gate/gate_urls.py`, new template e.g. `gate/student_detail.html`.
- **Sidebar/nav:** Show “Students” link for staff/faculty when you add read‑only access (e.g. in `templates/base/sidebar.html` or navbar by `user_role`).

If you tell me which of these you want first (e.g. “read-only list + detail view”), I can outline the exact decorator and template changes step by step.
