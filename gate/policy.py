"""
Time-policy + schedule-policy gate: decide ALLOW / DENY / REQUIRE REASON for IN/OUT
based on current time, student load slip schedule, and current state (inside/outside).
"""
import datetime
from django.utils import timezone

from .models import GateEntry, GatePolicy, StudentLoadSlip
from .services.import_loadslip import parse_schedule_safe

_WEEKDAY_NAMES = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def _current_school_year_semester(now=None):
    if now is None:
        now = timezone.now()
    if hasattr(now, 'date'):
        now = now.date()
    year = getattr(now, 'year', now.year)
    month = getattr(now, 'month', now.month)
    if month >= 8:
        return f'{year}-{year + 1}', '1st'
    if month >= 6:
        return f'{year - 1}-{year}', 'summer'
    return f'{year - 1}-{year}', '2nd'


def _get_slip_sessions_today(slip, today_day):
    sessions = []
    for subj in slip.subjects.all():
        if subj.schedule:
            for day, start_t, end_t in parse_schedule_safe(subj.schedule):
                if day == today_day:
                    sessions.append((start_t, end_t, subj.subject_code))
        else:
            if subj.day == today_day:
                sessions.append((subj.start_time, subj.end_time, subj.subject_code))
    return sessions


def get_gate_policy():
    """Return the active gate policy (first active one) or None to use hardcoded defaults."""
    return GatePolicy.objects.filter(is_active=True).first()


def get_student_sessions_today(student, now=None):
    """
    Return list of (start_time, end_time, subject_code) for today from student's load slip.
    Uses current school year/semester first; if no slip for current term, uses the most recent
    load slip for this student so gate logic still applies when term doesn't match exactly.
    """
    if now is None:
        now = timezone.localtime(timezone.now())
    weekday = now.weekday() if hasattr(now, 'weekday') else 0
    today_day = _WEEKDAY_NAMES[weekday]
    school_year, semester = _current_school_year_semester(now)
    slip = StudentLoadSlip.objects.filter(
        student=student,
        school_year=school_year,
        semester=semester,
    ).prefetch_related('subjects').first()
    if not slip:
        # Fallback: use most recent load slip for this student so gate blocks/allow based on schedule
        slip = StudentLoadSlip.objects.filter(student=student).prefetch_related('subjects').order_by('-school_year', '-updated_at').first()
    if not slip:
        return []
    return _get_slip_sessions_today(slip, today_day)


def has_load_slip(student, now=None):
    """True if student has any load slip (OUT logic is based on it). Uses current term first, then any slip."""
    if now is None:
        now = timezone.localtime(timezone.now())
    school_year, semester = _current_school_year_semester(now)
    if StudentLoadSlip.objects.filter(student=student, school_year=school_year, semester=semester).exists():
        return True
    return StudentLoadSlip.objects.filter(student=student).exists()


def has_class_after(student, now=None):
    """True if student has any class today with start_time > now."""
    now_time = (now or timezone.localtime(timezone.now())).time() if hasattr(now, 'time') else now
    sessions = get_student_sessions_today(student, now)
    for start_t, end_t, _ in sessions:
        if start_t > now_time:
            return True
    return False


def last_class_end_today(student, now=None):
    """Max end_time of all sessions today; None if no sessions."""
    sessions = get_student_sessions_today(student, now)
    if not sessions:
        return None
    return max(end_t for _, end_t, _ in sessions)


def next_class_starts_within_minutes(student, now=None, minutes=30):
    """
    True if student has a class starting within the next `minutes` (buffer rule).
    Returns (True, start_time, subject_code) or (False, None, None).
    """
    if now is None:
        now = timezone.localtime(timezone.now())
    now_time = now.time() if hasattr(now, 'time') else now
    # simple buffer: now + minutes (we work in time only for same-day)
    from datetime import timedelta
    now_dt = datetime.datetime.combine(now.date() if hasattr(now, 'date') else timezone.localdate(), now_time)
    limit_dt = now_dt + timedelta(minutes=minutes)
    limit_time = limit_dt.time()
    sessions = get_student_sessions_today(student, now)
    for start_t, end_t, subject_code in sorted(sessions, key=lambda x: x[0]):
        if now_time < start_t <= limit_time:
            return True, start_t, subject_code
    return False, None, None


def get_student_current_state(student, today=None, daily_gate_only=False):
    """
    Based on last SUCCESS scan today: last scan IN -> INSIDE, last scan OUT -> OUTSIDE, none -> OUTSIDE.
    Uses local day bounds so timezone matches gate entry list and dashboard.
    When daily_gate_only=True, only entries with event=None (daily gate) are considered.
    """
    if today is None:
        today = timezone.localdate()
    # Same formula as gate_views._local_day_bounds so "today" is consistent across policy, save_scan, entry_list.
    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min), tz)
    day_end = day_start + datetime.timedelta(days=1)
    qs = GateEntry.objects.filter(student=student, timestamp__gte=day_start, timestamp__lt=day_end)
    if daily_gate_only:
        qs = qs.filter(event__isnull=True)
    if hasattr(GateEntry, 'result'):
        qs = qs.filter(granted=True, result='SUCCESS')
    else:
        qs = qs.filter(granted=True)
    last = qs.order_by('-timestamp').first()
    if not last:
        return 'OUTSIDE'
    # Prefer scan_type; fallback to notes for legacy
    st = getattr(last, 'scan_type', None)
    if st:
        return 'INSIDE' if st == 'IN' else 'OUTSIDE'
    notes = (last.notes or '').strip().upper()
    return 'OUTSIDE' if notes == 'OUT' else 'INSIDE'


def evaluate_scan(student, scan_type, now=None, guard_override_reason=None, policy=None, daily_gate_only=False):
    """
    Apply time-policy + schedule-policy. Returns a dict:
      allowed: bool
      result: 'SUCCESS' | 'DENIED' | 'REQUIRE_REASON' | 'DUPLICATE'
      message: str (for UI / logs)
      out_reason_code: str (when allowed with reason)
      out_reason_text: str
      schedule_hint: str (e.g. "Class now: IT101 1:00–2:30" or "No class now")
      next_suggested: 'IN' | 'OUT'
      deny_reason: str (when denied, why)
      forced_out_no_in: bool (only when OUT allowed from OUTSIDE with guard reason)
    When daily_gate_only=True, current state is computed from daily gate entries only (event=None).

    Branch summary:
    IN:  duplicate INSIDE → DUPLICATE; before gate_open (no override) → DENIED;
         in lunch return window (strict) → DENIED; else → SUCCESS.
    OUT: state OUTSIDE + no reason → DUPLICATE; OUTSIDE + guard reason → SUCCESS (forced_out_no_in);
         in lunch window → SUCCESS (LUNCH); before/after lunch: in_class → guard else REQUIRE_REASON;
         class soon (buffer) → guard else REQUIRE_REASON; no more class today → ALL_CLASSES_DONE;
         after effective_out_until → ALL_CLASSES_DONE; else allow (NO_CLASS_WINDOW / gap).
    """
    if now is None:
        now = timezone.localtime(timezone.now())
    now_time = now.time() if hasattr(now, 'time') else now
    policy = policy or get_gate_policy()
    # Defaults if no policy row (lunch exit without reason: 11:59 AM–12:59 PM inclusive)
    gate_open = datetime.time(7, 0)
    lunch_out_start = datetime.time(11, 59, 0)
    lunch_in_start = datetime.time(12, 59, 0)
    lunch_exit_end = datetime.time(12, 59, 59)  # End of lunch OUT window (exit without reason through 12:59 PM)
    general_out_until = datetime.time(17, 0)
    strict_lunch_return = True
    out_buffer_minutes = 30
    if policy:
        gate_open = policy.gate_open_time
        lunch_out_start = policy.lunch_out_start
        lunch_in_start = policy.lunch_in_start
        # Lunch OUT window: from lunch_out_start through 12:59 PM (so students can exit without reason 11:59–12:59)
        lunch_exit_end = datetime.time(12, 59, 59) if lunch_in_start <= datetime.time(12, 59, 0) else lunch_in_start
        general_out_until = policy.general_out_until
        strict_lunch_return = policy.strict_lunch_return
        out_buffer_minutes = policy.out_buffer_minutes

    state = get_student_current_state(student, now.date() if hasattr(now, 'date') else timezone.localdate(), daily_gate_only=daily_gate_only)
    has_load_slip_val = has_load_slip(student, now)
    in_class_now_val, class_until, class_subject = in_class_now(student, now)
    has_later = has_class_after(student, now)
    last_end = last_class_end_today(student, now)
    next_soon, next_start, next_subject = next_class_starts_within_minutes(student, now, out_buffer_minutes)

    # Schedule hint for UI (based on load slip when present)
    if in_class_now_val and class_until and class_subject:
        schedule_hint = f"Class now: {class_subject} until {class_until.strftime('%I:%M %p')}"
    elif next_soon and next_start and next_subject:
        schedule_hint = f"Class in {out_buffer_minutes} min: {next_subject} at {next_start.strftime('%I:%M %p')}"
    elif has_later:
        schedule_hint = "Has class later today"
    else:
        schedule_hint = "No class now"
    if not has_load_slip_val:
        schedule_hint = "No load slip on file. " + (schedule_hint if schedule_hint else "Exit may require guard approval.")

    next_suggested = 'OUT' if state == 'INSIDE' else 'IN'

    # ---------- IN ----------
    if scan_type == 'IN':
        # Optional: require load slip for entry so gate is strictly based on class schedule
        if policy and getattr(policy, 'require_load_slip_for_entry', False) and not has_load_slip_val:
            return {
                'allowed': False,
                'result': 'DENIED',
                'message': 'No load slip on file. Please contact the registrar to add your class schedule.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': 'No load slip',
                'has_load_slip': False,
                'schedule_based': False,
            }
        if state == 'INSIDE':
            return {
                'allowed': False,
                'result': 'DUPLICATE',
                'message': 'Already inside. No duplicate IN.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'OUT',
                'deny_reason': 'Already inside',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }
        # Schedule-based entry restrictions
        # Deny outright if student has a load slip but there are no sessions today
        if has_load_slip_val and not in_class_now_val and not has_later:
            return {
                'allowed': False,
                'result': 'DENIED',
                'message': 'Based on your load slip: no classes today. Entry blocked.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': 'No class today',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }
        # If there are classes later but not currently in class, require a reason
        if has_load_slip_val and not in_class_now_val and has_later and not guard_override_reason:
            return {
                'allowed': False,
                'result': 'REQUIRE_REASON',
                'message': 'Based on your load slip: not currently in class. Provide a valid reason to enter.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': 'Not class time',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }
        # Gate open time
        if now_time < gate_open and not guard_override_reason:
            return {
                'allowed': False,
                'result': 'DENIED',
                'message': f'Gate opens at {gate_open.strftime("%I:%M %p")}.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': 'Before gate open',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }
        # Lunch window (11:59 AM–12:59 PM): allow both IN and OUT without reason — allow return from lunch during this window
        if lunch_out_start <= now_time <= lunch_exit_end:
            return {
                'allowed': True,
                'result': 'SUCCESS',
                'message': 'Return from lunch allowed (lunch window).',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'OUT',
                'deny_reason': '',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }
        return {
            'allowed': True,
            'result': 'SUCCESS',
            'message': 'Entry allowed.',
            'out_reason_code': '',
            'out_reason_text': '',
            'schedule_hint': schedule_hint,
            'next_suggested': 'OUT',
            'deny_reason': '',
            'has_load_slip': has_load_slip_val,
            'schedule_based': True,
        }

    # ---------- OUT ----------
    if scan_type == 'OUT':
        if state == 'OUTSIDE':
            if guard_override_reason:
                return {
                    'allowed': True,
                    'result': 'SUCCESS',
                    'message': 'Forced OUT recorded (no prior IN today). Guard reason saved for audit.',
                    'out_reason_code': 'OVERRIDE_BY_GUARD',
                    'out_reason_text': guard_override_reason,
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'IN',
                    'deny_reason': '',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                    'forced_out_no_in': True,
                }
            return {
                'allowed': False,
                'result': 'DUPLICATE',
                'message': 'Already outside. Scan IN first.',
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': 'Already outside',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }

        # Rule 1 — Lunch OUT window: 11:59 AM to 12:59 PM inclusive — exit allowed without reason
        # lunch_exit_end is 12:59:59 so the full 12:59 PM minute is included (even if policy has lunch_in_start = noon)
        if lunch_out_start <= now_time <= lunch_exit_end:
            return {
                'allowed': True,
                'result': 'SUCCESS',
                'message': 'Lunch break exit allowed.',
                'out_reason_code': 'LUNCH',
                'out_reason_text': guard_override_reason or 'Lunch break',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': '',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }

        # Rule 2 — Before lunch (morning): allow OUT only if NOT in class and (no class in buffer OR guard reason)
        if now_time < lunch_out_start:
            if in_class_now_val:
                if guard_override_reason:
                    return {
                        'allowed': True,
                        'result': 'SUCCESS',
                        'message': 'Early exit allowed (guard reason recorded).',
                        'out_reason_code': 'OVERRIDE_BY_GUARD',
                        'out_reason_text': guard_override_reason,
                        'schedule_hint': schedule_hint,
                        'next_suggested': 'IN',
                        'deny_reason': '',
                        'has_load_slip': has_load_slip_val,
                        'schedule_based': True,
                    }
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': f'Based on your load slip: class until {class_until.strftime("%I:%M %p") if class_until else "—"}. Enter a valid reason for early exit (for proof/audit).',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'In class',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            if has_later and not guard_override_reason:
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': 'Based on your load slip: you still have class later today. Provide a valid reason to leave.',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'Has class later',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            if next_soon and not guard_override_reason:
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': f'Based on your load slip: class starts at {next_start.strftime("%I:%M %p") if next_start else "—"}. Provide reason to leave.',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'Class soon',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            return {
                'allowed': True,
                'result': 'SUCCESS',
                'message': 'Exit allowed.',
                'out_reason_code': guard_override_reason and 'OVERRIDE_BY_GUARD' or 'NO_CLASS_WINDOW',
                'out_reason_text': guard_override_reason or 'No class in window',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': '',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }

        # Rule 3 & 4 — After lunch: after general_out_until use last class end (from load slip)
        effective_out_until = general_out_until
        if last_end and last_end > general_out_until:
            effective_out_until = last_end

        if now_time < effective_out_until:
            if in_class_now_val:
                if guard_override_reason:
                    return {
                        'allowed': True,
                        'result': 'SUCCESS',
                        'message': 'Early exit allowed (guard reason recorded).',
                        'out_reason_code': 'OVERRIDE_BY_GUARD',
                        'out_reason_text': guard_override_reason,
                        'schedule_hint': schedule_hint,
                        'next_suggested': 'IN',
                        'deny_reason': '',
                        'has_load_slip': has_load_slip_val,
                        'schedule_based': True,
                    }
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': f'Based on your load slip: class until {class_until.strftime("%I:%M %p") if class_until else "—"}. Enter a valid reason for early exit (for proof/audit).',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'In class',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            if next_soon and not guard_override_reason:
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': f'Based on your load slip: class starts at {next_start.strftime("%I:%M %p") if next_start else "—"}. Provide reason.',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'Class soon',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            if has_later and not guard_override_reason:
                return {
                    'allowed': False,
                    'result': 'REQUIRE_REASON',
                    'message': 'Based on your load slip: you still have class later today. Provide a valid reason to leave.',
                    'out_reason_code': '',
                    'out_reason_text': '',
                    'schedule_hint': schedule_hint,
                    'next_suggested': 'OUT',
                    'deny_reason': 'Has class later',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            if not has_later:
                return {
                    'allowed': True,
                    'result': 'SUCCESS',
                    'message': 'All classes done (per your load slip). You may exit without a valid reason.',
                    'out_reason_code': 'ALL_CLASSES_DONE',
                    'out_reason_text': guard_override_reason or 'All classes done',
                    'schedule_hint': 'All classes done for today. You can now exit without a valid reason.',
                    'next_suggested': 'IN',
                    'deny_reason': '',
                    'has_load_slip': has_load_slip_val,
                    'schedule_based': True,
                }
            return {
                'allowed': True,
                'result': 'SUCCESS',
                'message': 'Exit allowed (gap/return later).',
                'out_reason_code': guard_override_reason and 'OVERRIDE_BY_GUARD' or 'NO_CLASS_WINDOW',
                'out_reason_text': guard_override_reason or 'Gap',
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_reason': '',
                'has_load_slip': has_load_slip_val,
                'schedule_based': True,
            }

        # After effective_out_until (end of day / after last class per load slip)
        return {
            'allowed': True,
            'result': 'SUCCESS',
            'message': 'All classes done (per your load slip). You may exit without a valid reason.',
            'out_reason_code': 'ALL_CLASSES_DONE',
            'out_reason_text': guard_override_reason or 'All classes done',
            'schedule_hint': 'All classes done for today. You can now exit without a valid reason.',
            'next_suggested': 'IN',
            'deny_reason': '',
            'has_load_slip': has_load_slip_val,
            'schedule_based': True,
        }


def in_class_now(student, now=None):
    """
    Same semantics as gate_views._student_in_class_now: (in_class, class_until, subject_code).
    """
    if now is None:
        now = timezone.localtime(timezone.now())
    now_time = now.time() if hasattr(now, 'time') else now
    sessions = get_student_sessions_today(student, now)
    for start_t, end_t, subject_code in sorted(sessions, key=lambda x: x[1]):
        if start_t <= now_time < end_t:
            return True, end_t, subject_code
    return False, None, None
