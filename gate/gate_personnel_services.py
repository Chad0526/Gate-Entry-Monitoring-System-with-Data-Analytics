"""
Personnel gate services: notifications, activity logging, history, performance, realtime stats.

Used by staff/faculty at the gate (no separate guard account).
"""
import datetime
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from .models import (
    GateNotification, GateHandoverNote, GateHandoverNoteRead, GateActivityLog,
    GateEntry, GateIncident, GateShift, Student, Event, EventAttendance
)


class GateNotificationService:
    """
    Service for creating and managing guard notifications.
    Supports incident alerts, capacity warnings, shift reminders, and suspicious activity alerts.
    """
    
    @staticmethod
    def create_incident_alert(incident, broadcast=True):
        """
        Create an incident alert notification for guards.
        Priority is determined by incident reason (proxy/identity_mismatch = high, others = medium).
        
        Args:
            incident: GateIncident object
            broadcast: If True, send to all on-duty guards; if False, create single notification
            
        Returns:
            GateNotification object (or list if broadcast)
        """
        # Determine priority based on incident reason
        if incident.reason in ('proxy_attendance', 'identity_mismatch'):
            priority = 'high'
        else:
            priority = 'medium'
        
        # Build notification message
        if incident.student:
            title = f"Incident: {incident.get_reason_display()} - {incident.student.student_id}"
            message = (
                f"Student: {incident.student.get_full_name()}\n"
                f"Reason: {incident.get_reason_display()}\n"
                f"Details: {incident.details or '—'}"
            )
        else:
            title = f"Incident: {incident.get_reason_display()}"
            message = (
                f"Scanned ID: {incident.scanned_id or '—'}\n"
                f"Reason: {incident.get_reason_display()}\n"
                f"Details: {incident.details or '—'}"
            )
        
        if broadcast:
            # Broadcast to all guards currently on duty
            active_shifts = GateShift.objects.filter(shift_end__isnull=True).select_related('personnel')
            notifications = []
            for shift in active_shifts:
                notification = GateNotification.objects.create(
                    notification_type='incident',
                    priority=priority,
                    title=title,
                    message=message,
                    notify_user=shift.personnel,
                    broadcast=True,
                    related_incident=incident
                )
                notifications.append(notification)
            return notifications
        else:
            # Single notification
            notification = GateNotification.objects.create(
                notification_type='incident',
                priority=priority,
                title=title,
                message=message,
                broadcast=False,
                related_incident=incident
            )
            return notification
    
    @staticmethod
    def create_capacity_alert(event, current_count, capacity):
        """
        Create a capacity alert when event reaches 80% or 100%.
        
        Args:
            event: Event object
            current_count: Current number of attendees
            capacity: Maximum capacity
            
        Returns:
            List of GateNotification objects (broadcast to all on-duty guards)
        """
        if capacity <= 0:
            return []
        
        percentage = (current_count / capacity) * 100
        
        # Determine priority
        if percentage >= 100:
            priority = 'urgent'
        elif percentage >= 80:
            priority = 'high'
        else:
            return []  # Below threshold
        
        title = f"Capacity Alert: {event.name}"
        message = (
            f"Event is at {percentage:.0f}% capacity\n"
            f"Current: {current_count} / {capacity}\n"
            f"Location: {event.venue or '—'}"
        )
        
        # Broadcast to all on-duty guards
        active_shifts = GateShift.objects.filter(shift_end__isnull=True).select_related('personnel')
        notifications = []
        for shift in active_shifts:
            notification = GateNotification.objects.create(
                notification_type='capacity',
                priority=priority,
                title=title,
                message=message,
                notify_user=shift.personnel,
                broadcast=True,
                related_event=event
            )
            notifications.append(notification)
        
        return notifications
    
    @staticmethod
    def create_shift_reminder(guard, shift, minutes_remaining=30):
        """
        Create a shift reminder notification when shift is ending soon.
        
        Args:
            guard: User object (guard)
            shift: GateShift object
            minutes_remaining: Minutes until shift ends
            
        Returns:
            GateNotification object
        """
        title = "Shift Reminder"
        message = f"Your shift ends in {minutes_remaining} minutes. Prepare for handover."
        
        notification = GateNotification.objects.create(
            notification_type='shift_reminder',
            priority='medium',
            title=title,
            message=message,
            notify_user=guard,
            broadcast=False
        )
        return notification
    
    @staticmethod
    def create_suspicious_activity_alert(details, broadcast=True):
        """
        Create a suspicious activity alert for guards.
        
        Args:
            details: Description of suspicious activity
            broadcast: If True, send to all on-duty guards
            
        Returns:
            List of GateNotification objects if broadcast, single object otherwise
        """
        title = "Suspicious Activity Alert"
        message = details
        
        if broadcast:
            active_shifts = GateShift.objects.filter(shift_end__isnull=True).select_related('personnel')
            notifications = []
            for shift in active_shifts:
                notification = GateNotification.objects.create(
                    notification_type='suspicious',
                    priority='urgent',
                    title=title,
                    message=message,
                    notify_user=shift.personnel,
                    broadcast=True
                )
                notifications.append(notification)
            return notifications
        else:
            notification = GateNotification.objects.create(
                notification_type='suspicious',
                priority='urgent',
                title=title,
                message=message,
                broadcast=False
            )
            return notification
    
    @staticmethod
    def get_unread_notifications(guard):
        """
        Get all unread notifications for a guard (excluding expired ones).
        
        Args:
            guard: User object
            
        Returns:
            QuerySet of GateNotification objects
        """
        now = timezone.now()
        return GateNotification.objects.filter(
            notify_user=guard,
            is_read=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).order_by('-priority', '-created_at')
    
    @staticmethod
    def mark_as_read(notification_id, guard):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of notification
            guard: User object (must be the notify_user)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = GateNotification.objects.get(
                id=notification_id,
                notify_user=guard
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            return True
        except GateNotification.DoesNotExist:
            return False


class GateActivityLogger:
    """
    Service for logging all guard actions to create comprehensive audit trail.
    All logs are immutable once created.
    """
    
    @staticmethod
    def log_scan(guard, entry, device_id='', ip_address=None):
        """
        Log a gate scan action.
        
        Args:
            guard: User object
            entry: GateEntry object
            device_id: Scanner device ID
            ip_address: Client IP address
            
        Returns:
            GateActivityLog object
        """
        student_id = entry.student.student_id if entry.student else '—'
        scan_type = entry.scan_type or 'IN'
        result = 'GRANTED' if entry.granted else 'DENIED'
        
        description = f"Scanned {student_id} - {scan_type} ({result})"
        
        metadata_dict = {
            'scan_type': scan_type,
            'granted': entry.granted,
            'result': entry.result if hasattr(entry, 'result') else result
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type='scan',
            description=description,
            related_entry=entry,
            related_student=entry.student,
            device_id=device_id,
            ip_address=ip_address,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def log_override(guard, entry, reason, original_result, device_id='', ip_address=None):
        """
        Log an override decision (guard allows entry that would normally be denied).
        
        Args:
            guard: User object
            entry: GateEntry object
            reason: Reason for override
            original_result: What the result would have been without override
            device_id: Scanner device ID
            ip_address: Client IP address
            
        Returns:
            GateActivityLog object
        """
        student_id = entry.student.student_id if entry.student else '—'
        description = f"Override for {student_id} - Reason: {reason}"
        
        metadata_dict = {
            'reason': reason,
            'original_result': original_result,
            'final_result': 'GRANTED' if entry.granted else 'DENIED'
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type='override',
            description=description,
            related_entry=entry,
            related_student=entry.student,
            device_id=device_id,
            ip_address=ip_address,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def log_incident_creation(guard, incident, device_id='', ip_address=None):
        """
        Log incident report creation.
        
        Args:
            guard: User object
            incident: GateIncident object
            device_id: Scanner device ID
            ip_address: Client IP address
            
        Returns:
            GateActivityLog object
        """
        student_id = incident.student.student_id if incident.student else incident.scanned_id or '—'
        description = f"Reported incident: {incident.get_reason_display()} - {student_id}"
        
        metadata_dict = {
            'reason': incident.reason,
            'details': incident.details or ''
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type='incident',
            description=description,
            related_incident=incident,
            related_student=incident.student,
            device_id=device_id,
            ip_address=ip_address,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def log_shift_action(guard, action, shift, notes=''):
        """
        Log shift clock in/out action.
        
        Args:
            guard: User object
            action: 'shift_start' or 'shift_end'
            shift: GateShift object
            notes: Optional notes
            
        Returns:
            GateActivityLog object
        """
        if action == 'shift_start':
            description = f"Clocked in - Shift started"
        else:
            duration = (shift.shift_end - shift.shift_start).total_seconds() / 3600
            description = f"Clocked out - Shift duration: {duration:.1f} hours"
        
        metadata_dict = {
            'gate_post': shift.gate_post or '',
            'notes': notes
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type=action,
            description=description,
            related_shift=shift,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def log_note_creation(guard, note):
        """
        Log guard note creation.
        
        Args:
            guard: User object
            note: GateHandoverNote object
            
        Returns:
            GateActivityLog object
        """
        description = f"Created {note.get_priority_display()} priority note"
        
        metadata_dict = {
            'priority': note.priority,
            'content_preview': note.content[:100] if len(note.content) > 100 else note.content
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type='note',
            description=description,
            related_shift=note.shift,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def log_lookup(guard, query, results_count, device_id='', ip_address=None):
        """
        Log student lookup action.
        
        Args:
            guard: User object
            query: Search query
            results_count: Number of results found
            device_id: Scanner device ID
            ip_address: Client IP address
            
        Returns:
            GateActivityLog object
        """
        description = f"Student lookup: '{query}' ({results_count} results)"
        
        metadata_dict = {
            'query': query,
            'results_count': results_count
        }
        
        log = GateActivityLog.objects.create(
            personnel=guard,
            action_type='lookup',
            description=description,
            device_id=device_id,
            ip_address=ip_address,
            metadata=json.dumps(metadata_dict)
        )
        return log
    
    @staticmethod
    def get_guard_activity(guard, date_range=None):
        """
        Get activity logs for a guard within date range.
        
        Args:
            guard: User object
            date_range: Tuple of (start_date, end_date) or None for all
            
        Returns:
            QuerySet of GateActivityLog objects
        """
        logs = GateActivityLog.objects.filter(personnel=guard).order_by('-timestamp')
        
        if date_range:
            start_date, end_date = date_range
            logs = logs.filter(timestamp__gte=start_date, timestamp__lt=end_date)
        
        return logs
    
    @staticmethod
    def get_shift_activity(shift):
        """
        Get all activity logs for a specific shift.
        
        Args:
            shift: GateShift object
            
        Returns:
            QuerySet of GateActivityLog objects
        """
        if shift.shift_end:
            return GateActivityLog.objects.filter(
                personnel=shift.personnel,
                timestamp__gte=shift.shift_start,
                timestamp__lte=shift.shift_end
            ).order_by('-timestamp')
        else:
            # Ongoing shift
            return GateActivityLog.objects.filter(
                personnel=shift.personnel,
                timestamp__gte=shift.shift_start
            ).order_by('-timestamp')



class GateHistoryManager:
    """
    Service for managing guard access to historical data with 7-day restriction.
    Guards can only access last 7 days; admin/supervisor have unlimited access.
    """
    
    @staticmethod
    def can_access_date(guard, target_date):
        """
        Check if guard can access data for target_date.
        
        Args:
            guard: User object
            target_date: date object
            
        Returns:
            bool - True if access allowed
        """
        from gate_analytics.roles import get_user_role
        
        role = get_user_role(guard)
        
        # Admin and supervisor have unlimited access
        if role in ('admin', 'supervisor'):
            return True
        
        # Guards: last 7 days only
        today = timezone.localdate()
        earliest_allowed = today - timedelta(days=7)
        
        # No access to future dates
        if target_date > today:
            return False
        
        return target_date >= earliest_allowed
    
    @staticmethod
    def get_entries_last_7_days(guard, filters=None):
        """
        Get gate entries within last 7 days for guards (unlimited for admin/supervisor).
        
        Args:
            guard: User object
            filters: Dict with optional keys: from_date, to_date, q (search), scan_type
            
        Returns:
            QuerySet of GateEntry objects (max 500)
        """
        from gate_analytics.roles import get_user_role
        from gate.gate_views import _local_day_bounds
        
        role = get_user_role(guard)
        filters = filters or {}
        
        today = timezone.localdate()
        from_date = filters.get('from_date', today)
        to_date = filters.get('to_date', today)
        search_query = filters.get('q', '')
        scan_type = filters.get('scan_type', '')
        
        # Apply 7-day restriction for staff/faculty (gate operators)
        if role in ('staff', 'faculty'):
            earliest_allowed = today - timedelta(days=7)
            if from_date < earliest_allowed:
                from_date = earliest_allowed
            if to_date < earliest_allowed:
                to_date = earliest_allowed
            if to_date > today:
                to_date = today
        
        # Build query
        day_start, day_end = _local_day_bounds(from_date)
        to_day_start, to_day_end = _local_day_bounds(to_date)
        
        entries = GateEntry.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=to_day_end
        ).select_related('student', 'incident', 'event').order_by('-timestamp')
        
        # Apply search filter
        if search_query:
            entries = entries.filter(
                Q(student__student_id__icontains=search_query) |
                Q(student__first_name__icontains=search_query) |
                Q(student__last_name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        # Apply scan type filter
        if scan_type in ('IN', 'OUT'):
            entries = entries.filter(scan_type=scan_type)
        
        # Limit results
        return entries[:500]
    
    @staticmethod
    def get_visitor_history_last_7_days(guard):
        """
        Get visitor entries within last 7 days.
        
        Args:
            guard: User object
            
        Returns:
            QuerySet of VisitorVisit objects
        """
        from gate_analytics.roles import get_user_role
        from .models import VisitorVisit
        
        role = get_user_role(guard)
        today = timezone.localdate()
        
        if role in ('staff', 'faculty'):
            earliest_allowed = today - timedelta(days=7)
            start_date = timezone.make_aware(
                datetime.datetime.combine(earliest_allowed, datetime.time.min)
            )
        else:
            start_date = timezone.make_aware(
                datetime.datetime.combine(today - timedelta(days=30), datetime.time.min)
            )

        return VisitorVisit.objects.filter(
            checked_in_at__gte=start_date
        ).order_by('-checked_in_at')
    
    @staticmethod
    def get_incidents_last_7_days(guard):
        """
        Get incidents within last 7 days.
        
        Args:
            guard: User object
            
        Returns:
            QuerySet of GateIncident objects
        """
        from gate_analytics.roles import get_user_role
        
        role = get_user_role(guard)
        today = timezone.localdate()
        
        if role in ('staff', 'faculty'):
            earliest_allowed = today - timedelta(days=7)
            start_date = timezone.make_aware(
                datetime.datetime.combine(earliest_allowed, datetime.time.min)
            )
        else:
            start_date = timezone.make_aware(
                datetime.datetime.combine(today - timedelta(days=30), datetime.time.min)
            )

        return GateIncident.objects.filter(
            timestamp__gte=start_date
        ).order_by('-timestamp')
    
    @staticmethod
    def get_weekly_summary(guard, week_start):
        """
        Get weekly summary statistics.
        
        Args:
            guard: User object
            week_start: date object (Monday of the week)
            
        Returns:
            dict with summary statistics
        """
        from gate.gate_views import _local_day_bounds
        
        week_end = week_start + timedelta(days=7)
        day_start, _ = _local_day_bounds(week_start)
        _, day_end = _local_day_bounds(week_end)
        
        entries = GateEntry.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end
        )
        
        return {
            'total_entries': entries.filter(granted=True).count(),
            'denied_entries': entries.filter(granted=False).count(),
            'entries_in': entries.filter(scan_type='IN', granted=True).count(),
            'entries_out': entries.filter(scan_type='OUT', granted=True).count(),
            'incidents': GateIncident.objects.filter(
                timestamp__gte=day_start,
                timestamp__lt=day_end
            ).count()
        }
    
    @staticmethod
    def get_monthly_summary(guard, month, year):
        """
        Get monthly summary statistics.
        
        Args:
            guard: User object
            month: int (1-12)
            year: int
            
        Returns:
            dict with summary statistics
        """
        from gate.gate_views import _local_month_bounds
        
        month_start, month_end = _local_month_bounds(year, month)
        
        entries = GateEntry.objects.filter(
            timestamp__gte=month_start,
            timestamp__lt=month_end
        )
        
        return {
            'total_entries': entries.filter(granted=True).count(),
            'denied_entries': entries.filter(granted=False).count(),
            'entries_in': entries.filter(scan_type='IN', granted=True).count(),
            'entries_out': entries.filter(scan_type='OUT', granted=True).count(),
            'incidents': GateIncident.objects.filter(
                timestamp__gte=month_start,
                timestamp__lt=month_end
            ).count()
        }


class GatePerformanceTracker:
    """
    Service for calculating guard performance metrics.
    Tracks scans per hour, accuracy rate, incidents, and response times.
    """
    
    @staticmethod
    def get_shift_metrics(shift):
        """
        Calculate metrics for a specific shift.
        
        Args:
            shift: GateShift object
            
        Returns:
            dict with shift metrics
        """
        now = timezone.now()
        shift_end = shift.shift_end or now
        duration = (shift_end - shift.shift_start).total_seconds() / 3600  # hours
        
        entries = GateEntry.objects.filter(
            recorded_by=shift.personnel,
            timestamp__gte=shift.shift_start,
            timestamp__lte=shift_end
        )
        
        total_scans = entries.count()
        successful_scans = entries.filter(granted=True).count()
        denied_scans = entries.filter(granted=False).count()
        
        scans_per_hour = total_scans / duration if duration > 0 else 0
        accuracy_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
        
        incidents = GateActivityLog.objects.filter(
            personnel=shift.personnel,
            action_type='incident',
            timestamp__gte=shift.shift_start,
            timestamp__lte=shift_end
        ).count()
        
        overrides = GateActivityLog.objects.filter(
            personnel=shift.personnel,
            action_type='override',
            timestamp__gte=shift.shift_start,
            timestamp__lte=shift_end
        ).count()
        
        return {
            'duration_hours': round(duration, 2),
            'total_scans': total_scans,
            'successful_scans': successful_scans,
            'denied_scans': denied_scans,
            'scans_per_hour': round(scans_per_hour, 2),
            'accuracy_rate': round(accuracy_rate, 2),
            'incidents_reported': incidents,
            'overrides_made': overrides
        }
    
    @staticmethod
    def calculate_scans_per_hour(guard, date_range):
        """
        Calculate average scans per hour for a guard.
        
        Args:
            guard: User object
            date_range: Tuple of (start_datetime, end_datetime)
            
        Returns:
            float - scans per hour
        """
        start_date, end_date = date_range
        
        # Get all shifts in period
        shifts = GateShift.objects.filter(
            personnel=guard,
            shift_start__gte=start_date,
            shift_start__lt=end_date
        )
        
        total_hours = 0
        for shift in shifts:
            shift_end = shift.shift_end or timezone.now()
            duration = (shift_end - shift.shift_start).total_seconds() / 3600
            total_hours += duration
        
        if total_hours == 0:
            return 0
        
        total_scans = GateEntry.objects.filter(
            recorded_by=guard,
            timestamp__gte=start_date,
            timestamp__lt=end_date
        ).count()
        
        return total_scans / total_hours
    
    @staticmethod
    def calculate_accuracy_rate(guard, date_range):
        """
        Calculate accuracy rate (successful scans / total scans).
        
        Args:
            guard: User object
            date_range: Tuple of (start_datetime, end_datetime)
            
        Returns:
            float - accuracy rate (0-100)
        """
        start_date, end_date = date_range
        
        entries = GateEntry.objects.filter(
            recorded_by=guard,
            timestamp__gte=start_date,
            timestamp__lt=end_date
        )
        
        total_scans = entries.count()
        if total_scans == 0:
            return 0
        
        successful_scans = entries.filter(granted=True).count()
        return (successful_scans / total_scans) * 100
    
    @staticmethod
    def get_incident_response_time(guard, date_range):
        """
        Calculate average incident response time.
        
        Args:
            guard: User object
            date_range: Tuple of (start_datetime, end_datetime)
            
        Returns:
            timedelta - average response time
        """
        start_date, end_date = date_range
        
        incident_logs = GateActivityLog.objects.filter(
            personnel=guard,
            action_type='incident',
            timestamp__gte=start_date,
            timestamp__lt=end_date,
            related_incident__isnull=False
        ).select_related('related_incident')
        
        if not incident_logs.exists():
            return timedelta(seconds=0)
        
        total_response_time = timedelta(seconds=0)
        count = 0
        
        for log in incident_logs:
            response_time = log.timestamp - log.related_incident.timestamp
            total_response_time += response_time
            count += 1
        
        if count == 0:
            return timedelta(seconds=0)
        
        return total_response_time / count
    
    @staticmethod
    def get_performance_summary(guard, period_start, period_end):
        """
        Get comprehensive performance summary for a guard.
        
        Args:
            guard: User object
            period_start: datetime
            period_end: datetime
            
        Returns:
            dict with all performance metrics
        """
        date_range = (period_start, period_end)
        
        # Calculate all metrics
        entries = GateEntry.objects.filter(
            recorded_by=guard,
            timestamp__gte=period_start,
            timestamp__lt=period_end
        )
        
        total_scans = entries.count()
        successful_scans = entries.filter(granted=True).count()
        denied_scans = entries.filter(granted=False).count()
        
        accuracy_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
        
        # Calculate total hours worked
        shifts = GateShift.objects.filter(
            personnel=guard,
            shift_start__gte=period_start,
            shift_start__lt=period_end
        )
        
        total_hours = 0
        for shift in shifts:
            shift_end = shift.shift_end or timezone.now()
            duration = (shift_end - shift.shift_start).total_seconds() / 3600
            total_hours += duration
        
        scans_per_hour = total_scans / total_hours if total_hours > 0 else 0
        
        # Activity logs
        activity_logs = GateActivityLog.objects.filter(
            personnel=guard,
            timestamp__gte=period_start,
            timestamp__lt=period_end
        )
        
        incidents_reported = activity_logs.filter(action_type='incident').count()
        overrides_made = activity_logs.filter(action_type='override').count()
        
        # Average response time
        avg_response_time = GatePerformanceTracker.get_incident_response_time(guard, date_range)
        
        return {
            'personnel': guard,
            'period_start': period_start,
            'period_end': period_end,
            'total_scans': total_scans,
            'successful_scans': successful_scans,
            'denied_scans': denied_scans,
            'accuracy_rate': round(accuracy_rate, 2),
            'scans_per_hour': round(scans_per_hour, 2),
            'incidents_reported': incidents_reported,
            'overrides_made': overrides_made,
            'average_response_time': avg_response_time,
            'shifts_worked': shifts.count(),
            'total_hours': round(total_hours, 2)
        }



class RealtimeDashboardService:
    """
    Service for providing real-time dashboard statistics and activity feeds.
    """
    
    @staticmethod
    def get_current_stats():
        """
        Get current dashboard statistics.
        
        Returns:
            dict with current stats
        """
        now = timezone.now()
        today = timezone.localdate()
        
        # Get today's entries
        from gate.gate_views import _local_day_bounds
        day_start, day_end = _local_day_bounds(today)
        
        today_entries = GateEntry.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end
        )
        
        return {
            'currently_inside': RealtimeDashboardService.get_currently_inside_count(),
            'total_entries_today': today_entries.filter(granted=True).count(),
            'denied_today': today_entries.filter(granted=False).count(),
            'incidents_today': GateIncident.objects.filter(
                timestamp__gte=day_start,
                timestamp__lt=day_end
            ).count(),
            'active_guards': GateShift.objects.filter(shift_end__isnull=True).count(),
            'timestamp': now
        }

    @staticmethod
    def get_guard_recent_entries(limit=25):
        """Today's gate scans as JSON-safe rows for the guard wall display."""
        from gate.gate_views import _local_day_bounds
        today = timezone.localdate()
        day_start, day_end = _local_day_bounds(today)
        qs = GateEntry.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end,
        ).select_related('student', 'event', 'visitor_visit').order_by('-timestamp')[:limit]
        rows = []
        for e in qs:
            if e.student_id:
                who = e.student.get_full_name()
                who_id = e.student.student_id
            elif e.visitor_visit_id:
                who = e.visitor_visit.full_name
                who_id = 'Visitor'
            else:
                who = (e.notes or 'Unknown')[:120]
                who_id = '—'
            event_label = e.event.name if e.event_id else None
            rows.append({
                'time': timezone.localtime(e.timestamp).strftime('%H:%M:%S'),
                'who': who,
                'who_id': who_id,
                'direction': e.scan_type or '—',
                'granted': e.granted,
                'event': event_label,
            })
        return rows
    
    @staticmethod
    def get_currently_inside_count():
        """
        Calculate number of people currently inside campus TODAY.
        Only counts entries from today that haven't been matched with an exit.
        
        Returns:
            int - count of people inside
        """
        # Get today's date bounds
        from gate.gate_views import _local_day_bounds
        today = timezone.localdate()
        day_start, day_end = _local_day_bounds(today)
        
        # Get all students who have entered TODAY but not exited
        # Latest entry per student TODAY should be IN and granted
        from django.db.models import Max
        
        latest_entries = GateEntry.objects.filter(
            granted=True,
            timestamp__gte=day_start,
            timestamp__lt=day_end
        ).values('student').annotate(
            latest_timestamp=Max('timestamp')
        )
        
        inside_count = 0
        for entry_data in latest_entries:
            if entry_data['student'] is None:
                continue
            try:
                latest_entry = GateEntry.objects.get(
                    student_id=entry_data['student'],
                    timestamp=entry_data['latest_timestamp']
                )
            except GateEntry.DoesNotExist:
                continue
            if latest_entry.scan_type == 'IN':
                inside_count += 1
        
        return inside_count
    
    @staticmethod
    def get_hourly_activity_chart():
        """
        Get hourly activity data for the last 24 hours.
        
        Returns:
            list of dicts with hour and count (24 data points)
        """
        now = timezone.now()
        start_time = now - timedelta(hours=24)
        
        # Initialize 24 hours with 0 counts
        hourly_data = []
        for i in range(24):
            hour_start = start_time + timedelta(hours=i)
            hourly_data.append({
                'hour': hour_start.hour,
                'count': 0,
                'timestamp': hour_start
            })
        
        # Get entries in last 24 hours
        entries = GateEntry.objects.filter(
            timestamp__gte=start_time,
            timestamp__lt=now,
            granted=True
        )
        
        # Count entries per hour
        for entry in entries:
            hour_index = int((entry.timestamp - start_time).total_seconds() / 3600)
            if 0 <= hour_index < 24:
                hourly_data[hour_index]['count'] += 1
        
        return hourly_data
    
    @staticmethod
    def get_recent_activity_feed(limit=20):
        """
        Get recent activity feed (entries, incidents, shifts).
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            list of dicts with activity items
        """
        now = timezone.now()
        recent_cutoff = now - timedelta(hours=8)
        
        activities = []
        
        # Recent entries
        recent_entries = GateEntry.objects.filter(
            timestamp__gte=recent_cutoff
        ).select_related('student', 'recorded_by').order_by('-timestamp')[:limit]
        
        for entry in recent_entries:
            student_name = entry.student.get_full_name() if entry.student else 'Unknown'
            activities.append({
                'type': 'entry',
                'timestamp': entry.timestamp,
                'description': f"{student_name} - {entry.scan_type} ({'GRANTED' if entry.granted else 'DENIED'})",
                'icon': 'check' if entry.granted else 'times',
                'priority': 'normal'
            })
        
        # Recent incidents
        recent_incidents = GateIncident.objects.filter(
            timestamp__gte=recent_cutoff
        ).select_related('student').order_by('-timestamp')[:limit]
        
        for incident in recent_incidents:
            student_name = incident.student.get_full_name() if incident.student else incident.scanned_id or 'Unknown'
            activities.append({
                'type': 'incident',
                'timestamp': incident.timestamp,
                'description': f"Incident: {incident.get_reason_display()} - {student_name}",
                'icon': 'exclamation-triangle',
                'priority': 'high'
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:limit]
    
    @staticmethod
    def get_shift_summary(guard):
        """
        Get current shift summary for a guard.
        
        Args:
            guard: User object
            
        Returns:
            dict with shift summary or None if no active shift
        """
        try:
            active_shift = GateShift.objects.get(personnel=guard, shift_end__isnull=True)
        except GateShift.DoesNotExist:
            return None
        
        now = timezone.now()
        duration = (now - active_shift.shift_start).total_seconds() / 3600
        
        # Get shift metrics
        metrics = GatePerformanceTracker.get_shift_metrics(active_shift)
        
        return {
            'shift': active_shift,
            'duration_hours': round(duration, 2),
            'metrics': metrics
        }
    
    @staticmethod
    def get_active_alerts():
        """
        Get active alerts (high priority incidents, capacity warnings).
        
        Returns:
            list of alert dicts
        """
        now = timezone.now()
        recent_cutoff = now - timedelta(hours=2)
        
        alerts = []
        
        # Recent high-priority incidents
        high_priority_incidents = GateIncident.objects.filter(
            timestamp__gte=recent_cutoff,
            reason__in=('proxy_attendance', 'identity_mismatch', 'suspicious_behavior')
        ).order_by('-timestamp')[:5]
        
        for incident in high_priority_incidents:
            student_name = incident.student.get_full_name() if incident.student else incident.scanned_id or 'Unknown'
            alerts.append({
                'type': 'incident',
                'priority': 'high',
                'title': f"{incident.get_reason_display()}",
                'message': f"{student_name}",
                'timestamp': incident.timestamp
            })
        
        return alerts


class GateHandoverNotesManager:
    """
    Service for managing guard shift handover notes.
    """
    
    @staticmethod
    def create_note(guard, content, priority='normal', shift=None):
        """
        Create a new guard note.
        
        Args:
            guard: User object
            content: Note content (max 2000 chars)
            priority: 'low', 'normal', 'high', 'urgent'
            shift: GateShift object (optional)
            
        Returns:
            GateHandoverNote object
        """
        if len(content) > 2000:
            content = content[:2000]
        
        note = GateHandoverNote.objects.create(
            personnel=guard,
            shift=shift,
            priority=priority,
            content=content
        )
        
        # Log note creation
        GateActivityLogger.log_note_creation(guard, note)
        
        return note
    
    @staticmethod
    def get_recent_notes(limit=10):
        """
        Get recent notes from all guards.
        
        Args:
            limit: Maximum number of notes to return
            
        Returns:
            QuerySet of GateHandoverNote objects
        """
        return GateHandoverNote.objects.select_related(
            'guard', 'shift'
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_unread_notes(guard, limit=10):
        """
        Get unread notes for a guard.
        
        Args:
            guard: User object
            limit: Maximum number of notes to return
            
        Returns:
            QuerySet of GateHandoverNote objects
        """
        # Get notes that this guard hasn't read yet
        read_note_ids = GateHandoverNoteRead.objects.filter(
            personnel=guard
        ).values_list('note_id', flat=True)
        
        return GateHandoverNote.objects.exclude(
            id__in=read_note_ids
        ).exclude(
            personnel=guard  # Exclude own notes
        ).select_related('personnel', 'shift').order_by('-created_at')[:limit]
    
    @staticmethod
    def mark_note_read(note_id, guard):
        """
        Mark a note as read by a guard.
        
        Args:
            note_id: ID of GateHandoverNote
            guard: User object
            
        Returns:
            GateHandoverNoteRead object or None if already read
        """
        try:
            note = GateHandoverNote.objects.get(id=note_id)
        except GateHandoverNote.DoesNotExist:
            return None
        
        # Create read record (unique constraint prevents duplicates)
        read_record, created = GateHandoverNoteRead.objects.get_or_create(
            note=note,
            personnel=guard
        )
        
        return read_record if created else None
    
    @staticmethod
    def search_notes(query='', date_range=None, priority=None, limit=50):
        """
        Search notes with filters.
        
        Args:
            query: Search query for content
            date_range: Tuple of (start_date, end_date)
            priority: Priority filter
            limit: Maximum results
            
        Returns:
            QuerySet of GateHandoverNote objects
        """
        notes = GateHandoverNote.objects.select_related('personnel', 'shift').order_by('-created_at')
        
        if query:
            notes = notes.filter(content__icontains=query)
        
        if date_range:
            start_date, end_date = date_range
            notes = notes.filter(
                created_at__gte=start_date,
                created_at__lt=end_date
            )
        
        if priority:
            notes = notes.filter(priority=priority)
        
        return notes[:limit]


class StudentLookupService:
    """
    Service for quick student information lookup.
    """
    
    @staticmethod
    def lookup_by_id(student_id):
        """
        Lookup student by ID.
        
        Args:
            student_id: Student ID string
            
        Returns:
            Student object or None
        """
        try:
            return Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return None
    
    @staticmethod
    def lookup_by_name(name_query, limit=10):
        """
        Lookup students by name (first or last).
        
        Args:
            name_query: Name search query
            limit: Maximum results (default 10)
            
        Returns:
            QuerySet of Student objects
        """
        if len(name_query) < 3:
            return Student.objects.none()
        
        students = Student.objects.filter(
            Q(first_name__icontains=name_query) |
            Q(last_name__icontains=name_query) |
            Q(middle_name__icontains=name_query)
        ).order_by('last_name', 'first_name')[:limit]
        
        return students
    
    @staticmethod
    def get_current_schedule(student):
        """Gate no longer stores per-student class schedules; return None."""
        return None

    @staticmethod
    def get_today_schedule(student):
        """No load-slip schedule; empty list for API compatibility."""
        return []

    @staticmethod
    def verify_class_time(student):
        """No class-schedule integration at the daily gate."""
        return {
            'has_class': False,
            'message': 'Daily gate does not use class periods.',
        }

    @staticmethod
    def get_recent_entries(student, days=3):
        """
        Get recent gate entries for student.
        
        Args:
            student: Student object
            days: Number of days to look back (default 3)
            
        Returns:
            QuerySet of GateEntry objects
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        return GateEntry.objects.filter(
            student=student,
            timestamp__gte=cutoff
        ).order_by('-timestamp')



def check_event_capacity_and_alert(event):
    """Capacity alerting removed (maximum_attende field dropped)."""
    return {'status': 'no_capacity_limit', 'alerts_created': []}
