# QR Code Scan Flow and Load Slip Logic

## Summary

**Daily gate scanning (student QR at the main gate) is based on the student's load slip.** When no event is selected in the Gate Scan UI, every IN/OUT decision uses the student's class schedule from `StudentLoadSlip` and `LoadSlipSubject`.

## Flow

1. **Guard scans student QR** → Gate Scan page sends `POST /gate/save-scan/` with `student_id` (from QR) and optionally `event_id`.
2. **No event selected** (`event_id` empty) → **Daily gate path** in `save_scan`:
   - Uses `get_student_current_state(student, today, daily_gate_only=True)` for IN/OUT state.
   - Calls `evaluate_scan(student, status, now, daily_gate_only=True)` in `gate/policy.py`.
   - `evaluate_scan` uses:
     - `get_student_sessions_today(student, now)` → from `StudentLoadSlip` + `LoadSlipSubject` (current term or most recent slip).
     - `has_load_slip`, `in_class_now`, `has_class_after`, `last_class_end_today`, `next_class_starts_within_minutes`.
   - **IN**: Allowed only when currently in class, in lunch window, or (if no load slip) after gate open; denied if load slip says "no classes today" or "not in class" (unless guard override).
   - **OUT**: Allowed/denied/require-reason based on load slip (in class, class soon, all classes done, lunch window, etc.).
3. **Event selected** (`event_id` set) → **Event path** in `save_scan`:
   - Validates event audience and duplicate IN only. Load slip is **not** used for event attendance (event may be outside class hours).

## Key code

- **Scan entry**: `gate/gate_views.py` → `save_scan()`.
- **Daily gate policy**: `gate/policy.py` → `evaluate_scan()`, `get_student_sessions_today()`, `has_load_slip()`, `in_class_now()`, etc.
- **Load slip data**: `gate/models.py` → `StudentLoadSlip`, `LoadSlipSubject`; `gate/services/import_loadslip.py` for import.

## Optional: Require load slip for entry

When **Gate Policy** has **Require load slip for entry** enabled, students **without** any load slip are denied entry (IN) with a message to contact the registrar. This keeps gate access strictly based on having a class schedule on file.
