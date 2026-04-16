"""
Daily gate policy for IN/OUT (no class schedule / load slips).

College students may enter and leave the campus directly; we only enforce
duplicate IN when already inside, duplicate OUT when already outside, and
staff override when recording OUT without a prior IN the same day.
"""
import datetime
import math

from django.conf import settings
from django.utils import timezone

from .models import GateEntry, GatePolicy


def daily_gate_repeat_cooldown():
    """Minimum wait for daily gate repeat rules. Used with GATE_SCAN_REPEAT_COOLDOWN_SCOPE in save_scan / policy."""
    secs = int(getattr(settings, 'GATE_SCAN_REPEAT_COOLDOWN_SECONDS', 30))
    return datetime.timedelta(seconds=max(1, secs))


def format_cooldown_duration(cooldown_td):
    """Human-readable window length (e.g. '30 second(s)' or '5 minute(s)')."""
    secs = max(1, int(cooldown_td.total_seconds()))
    if secs < 60:
        return f'{secs} second(s)'
    mins = (secs + 59) // 60
    return f'{mins} minute(s)'


def format_cooldown_wait_remaining(secs_left: float) -> str:
    """Human-readable remaining wait from a seconds count."""
    secs = max(0, int(math.ceil(secs_left)))
    if secs < 60:
        return f'{max(1, secs)} second(s)'
    mins = max(1, (secs + 59) // 60)
    return f'{mins} minute(s)'


def get_gate_policy():
    """Return the active gate policy (first active one) or None."""
    return GatePolicy.objects.filter(is_active=True).first()


def get_student_current_state(student, today=None, daily_gate_only=False):
    """
    Based on last SUCCESS scan today: last scan IN -> INSIDE, last scan OUT -> OUTSIDE, none -> OUTSIDE.
    Uses local day bounds so timezone matches gate entry list and dashboard.
    When daily_gate_only=True, only entries with event=None (daily gate) are considered.
    """
    if today is None:
        today = timezone.localdate()
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
    st = getattr(last, 'scan_type', None)
    if st:
        return 'INSIDE' if st == 'IN' else 'OUTSIDE'
    notes = (last.notes or '').strip().upper()
    return 'OUTSIDE' if notes == 'OUT' else 'INSIDE'


def _local_day_bounds_for_date(today):
    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min), tz)
    day_end = day_start + datetime.timedelta(days=1)
    return day_start, day_end


def _last_successful_daily_gate_entry(student, today):
    """Most recent successful daily gate (event=None) entry for the local calendar day, or None."""
    day_start, day_end = _local_day_bounds_for_date(today)
    qs = GateEntry.objects.filter(
        student=student,
        event__isnull=True,
        timestamp__gte=day_start,
        timestamp__lt=day_end,
    )
    if hasattr(GateEntry, 'result'):
        qs = qs.filter(granted=True, result='SUCCESS')
    else:
        qs = qs.filter(granted=True)
    return qs.order_by('-timestamp').first()


def _entry_is_in_direction(entry):
    st = getattr(entry, 'scan_type', None)
    if st:
        return st == 'IN'
    return (entry.notes or '').strip().upper() != 'OUT'


def evaluate_scan(student, scan_type, now=None, personnel_override_reason=None, policy=None, daily_gate_only=False):
    """
    College-mode daily gate: allow IN/OUT based on current state only (no schedule).

    Returns dict keys expected by gate_scan / save_scan JSON.
    """
    if now is None:
        now = timezone.localtime(timezone.now())
    state = get_student_current_state(
        student,
        now.date() if hasattr(now, 'date') else timezone.localdate(),
        daily_gate_only=daily_gate_only,
    )
    schedule_hint = 'Daily gate — check in when arriving and check out when leaving.'
    schedule_based = False
    today = now.date() if hasattr(now, 'date') else timezone.localdate()
    now_local = (
        timezone.localtime(now)
        if timezone.is_aware(now)
        else timezone.make_aware(now, timezone.get_current_timezone())
    )
    cooldown_td = daily_gate_repeat_cooldown()
    cooldown_human = format_cooldown_duration(cooldown_td)

    if scan_type == 'IN':
        if state == 'INSIDE':
            # Allow a new IN if the last IN was long enough ago (multiple trips per day).
            if daily_gate_only:
                last_ent = _last_successful_daily_gate_entry(student, today)
                if last_ent and _entry_is_in_direction(last_ent):
                    last_ts = timezone.localtime(last_ent.timestamp)
                    if now_local - last_ts >= cooldown_td:
                        return {
                            'allowed': True,
                            'result': 'SUCCESS',
                            'message': 'Entry allowed.',
                            'out_reason_code': '',
                            'out_reason_text': '',
                            'schedule_hint': schedule_hint,
                            'next_suggested': 'OUT',
                            'deny_detail': '',
                            'schedule_based': schedule_based,
                        }
                dup_msg = (
                    f'Already inside. No duplicate IN within {cooldown_human} — scan OUT first or wait.'
                )
            else:
                dup_msg = 'Already inside. No duplicate IN.'
            return {
                'allowed': False,
                'result': 'DUPLICATE',
                'message': dup_msg,
                'out_reason_code': '',
                'out_reason_text': '',
                'schedule_hint': schedule_hint,
                'next_suggested': 'OUT',
                'deny_detail': 'Already inside',
                'schedule_based': schedule_based,
            }
        return {
            'allowed': True,
            'result': 'SUCCESS',
            'message': 'Entry allowed.',
            'out_reason_code': '',
            'out_reason_text': '',
            'schedule_hint': schedule_hint,
            'next_suggested': 'OUT',
            'deny_detail': '',
            'schedule_based': schedule_based,
        }

    # OUT
    if state == 'OUTSIDE':
        if personnel_override_reason:
            return {
                'allowed': True,
                'result': 'SUCCESS',
                'message': 'Forced OUT recorded (no prior IN today). Staff note saved for audit.',
                'out_reason_code': 'OVERRIDE_BY_PERSONNEL',
                'out_reason_text': personnel_override_reason,
                'schedule_hint': schedule_hint,
                'next_suggested': 'IN',
                'deny_detail': '',
                'schedule_based': schedule_based,
                'forced_out_no_in': True,
            }
        if daily_gate_only:
            last_ent = _last_successful_daily_gate_entry(student, today)
            if last_ent and not _entry_is_in_direction(last_ent):
                last_ts = timezone.localtime(last_ent.timestamp)
                elapsed = now_local - last_ts
                if elapsed < cooldown_td:
                    secs_left = (cooldown_td - elapsed).total_seconds()
                    wait_human = format_cooldown_wait_remaining(secs_left)
                    return {
                        'allowed': False,
                        'result': 'DUPLICATE',
                        'message': f'Please wait {wait_human} before scanning again.',
                        'out_reason_code': '',
                        'out_reason_text': '',
                        'schedule_hint': schedule_hint,
                        'next_suggested': 'IN',
                        'deny_detail': 'Repeat scan too soon',
                        'schedule_based': schedule_based,
                    }
        return {
            'allowed': False,
            'result': 'DUPLICATE',
            'message': 'Already outside. Scan IN first.',
            'out_reason_code': '',
            'out_reason_text': '',
            'schedule_hint': schedule_hint,
            'next_suggested': 'IN',
            'deny_detail': 'Already outside',
            'schedule_based': schedule_based,
        }

    return {
        'allowed': True,
        'result': 'SUCCESS',
        'message': 'Exit allowed.',
        'out_reason_code': (personnel_override_reason and 'OVERRIDE_BY_PERSONNEL') or 'OTHER',
        'out_reason_text': personnel_override_reason or '',
        'schedule_hint': schedule_hint,
        'next_suggested': 'IN',
        'deny_detail': '',
        'schedule_based': schedule_based,
    }
