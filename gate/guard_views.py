"""
Guard Account Enhancement Views
Provides views for guard dashboard, notifications, performance, and activity logging.
"""
import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Case, When

from gate_analytics.roles import get_user_role
from .models import (
    GuardNotification, GuardNote, GuardShift, GuardActivityLog,
    Student, GateEntry
)
from .guard_services import (
    GuardNotificationService, GuardActivityLogger, GuardHistoryManager,
    GuardPerformanceTracker, RealtimeDashboardService, GuardNotesManager,
    StudentLookupService
)


def _is_guard(user):
    """Check if user is in Guard group."""
    return user.groups.filter(name='Guard').exists()


def _is_supervisor_or_admin(user):
    """Check if user is supervisor, staff, or admin."""
    role = get_user_role(user)
    return role in ('admin', 'supervisor', 'staff')


@login_required
def guard_dashboard_view(request):
    """
    Guard dashboard with real-time stats, notifications, and activity feed.
    """
    # Check Guard group membership
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Get current shift information
    try:
        current_shift = GuardShift.objects.get(
            guard=request.user,
            shift_end__isnull=True
        )
    except GuardShift.DoesNotExist:
        current_shift = None
    
    # Get dashboard stats
    stats = RealtimeDashboardService.get_current_stats()
    
    # Get hourly activity chart
    hourly_data = RealtimeDashboardService.get_hourly_activity_chart()
    
    # Get recent activity feed
    recent_activity = RealtimeDashboardService.get_recent_activity_feed(limit=20)
    
    # Get shift summary if active
    shift_summary = None
    if current_shift:
        shift_summary = RealtimeDashboardService.get_shift_summary(request.user)
    
    # Get active alerts
    active_alerts = RealtimeDashboardService.get_active_alerts()
    
    # Get unread notifications
    unread_notifications = GuardNotificationService.get_unread_notifications(request.user)[:5]
    
    # Get unread notes
    unread_notes = GuardNotesManager.get_unread_notes(request.user, limit=5)
    
    context = {
        'current_shift': current_shift,
        'shift_summary': shift_summary,
        'stats': stats,
        'hourly_data': hourly_data,
        'recent_activity': recent_activity,
        'active_alerts': active_alerts,
        'unread_notifications': unread_notifications,
        'unread_notes': unread_notes,
    }
    
    return render(request, 'gate/guard_dashboard.html', context)


@login_required
def guard_entry_list_view(request):
    """
    Guard entry list with 7-day restriction and filtering.
    """
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Get filters from request
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')
    search_query = request.GET.get('q', '')
    scan_type = request.GET.get('scan_type', '')
    
    today = timezone.localdate()
    
    # Parse dates
    try:
        from_date = timezone.datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else today
    except ValueError:
        from_date = today
    
    try:
        to_date = timezone.datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else today
    except ValueError:
        to_date = today
    
    # Store original dates for warning
    original_from_date = from_date
    original_to_date = to_date
    
    # Build filters dict
    filters = {
        'from_date': from_date,
        'to_date': to_date,
        'q': search_query,
        'scan_type': scan_type
    }
    
    # Get entries with 7-day restriction applied
    entries = GuardHistoryManager.get_entries_last_7_days(request.user, filters)
    
    # Check if dates were adjusted
    date_adjusted = False
    role = get_user_role(request.user)
    if role == 'guard':
        earliest_allowed = today - timedelta(days=7)
        if original_from_date < earliest_allowed or original_to_date < earliest_allowed:
            date_adjusted = True
            messages.warning(
                request,
                f"Date range adjusted to last 7 days (from {earliest_allowed}). "
                "Guards can only access recent history."
            )
    
    # Paginate results (max 500 per page)
    paginator = Paginator(entries, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'entries': page_obj,
        'from_date': from_date,
        'to_date': to_date,
        'search_query': search_query,
        'scan_type': scan_type,
        'date_adjusted': date_adjusted,
    }
    
    return render(request, 'gate/guard_entry_list.html', context)


@login_required
def guard_notifications_view(request):
    """
    Guard notifications page with filtering and ordering.
    """
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Get all notifications for current guard
    now = timezone.now()
    notifications = GuardNotification.objects.filter(
        target_guard=request.user
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).order_by(
        # Order by priority (urgent, high, medium, low)
        Case(
            When(priority='urgent', then=0),
            When(priority='high', then=1),
            When(priority='medium', then=2),
            When(priority='low', then=3),
            default=4
        ),
        '-created_at'
    )
    
    # Paginate
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notifications': page_obj,
    }
    
    return render(request, 'gate/guard_notifications.html', context)


@login_required
def mark_notification_read_view(request):
    """
    AJAX endpoint to mark notification as read.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    if not _is_guard(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Try to get notification_id from POST data or JSON body
    notification_id = request.POST.get('notification_id')
    if not notification_id and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
        except (json.JSONDecodeError, ValueError):
            pass
    
    if not notification_id:
        return JsonResponse({'success': False, 'error': 'notification_id required'}, status=400)
    
    try:
        notification_id = int(notification_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid notification_id'}, status=400)
    
    success = GuardNotificationService.mark_as_read(notification_id, request.user)
    
    if success:
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Notification not found or already read'}, status=404)


@login_required
def guard_performance_view(request):
    """
    Guard performance metrics page.
    """
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Guards can only view their own metrics
    guard = request.user
    
    # Get date range from request (default to current month)
    today = timezone.now()
    
    # Parse date range
    period_str = request.GET.get('period', 'month')
    
    if period_str == 'week':
        period_start = today - timedelta(days=7)
    elif period_str == 'month':
        period_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period_str == 'year':
        period_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        period_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    period_end = today
    
    # Get performance summary
    performance = GuardPerformanceTracker.get_performance_summary(
        guard=guard,
        period_start=period_start,
        period_end=period_end
    )
    
    context = {
        'performance': performance,
        'period': period_str,
        'period_start': period_start,
        'period_end': period_end,
    }
    
    return render(request, 'gate/guard_performance.html', context)


@login_required
def guard_clock_in_view(request):
    """
    Clock in to start a shift.
    """
    if request.method != 'POST':
        return redirect('guard-dashboard')
    
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Check if already clocked in
    existing_shift = GuardShift.objects.filter(
        guard=request.user,
        shift_end__isnull=True
    ).first()
    
    if existing_shift:
        messages.warning(request, "You are already clocked in.")
        return redirect('guard-dashboard')
    
    # Get gate post from form
    gate_post = request.POST.get('gate_post', '')
    
    # Create new shift
    shift = GuardShift.objects.create(
        guard=request.user,
        shift_start=timezone.now(),
        gate_post=gate_post
    )
    
    # Log shift start
    GuardActivityLogger.log_shift_action(
        guard=request.user,
        action='shift_start',
        shift=shift
    )
    
    messages.success(request, "Clocked in successfully. Have a great shift!")
    return redirect('guard-dashboard')


@login_required
def guard_clock_out_view(request):
    """
    Clock out to end a shift with optional handover note.
    """
    if request.method != 'POST':
        return redirect('guard-dashboard')
    
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Get active shift
    try:
        shift = GuardShift.objects.get(
            guard=request.user,
            shift_end__isnull=True
        )
    except GuardShift.DoesNotExist:
        messages.error(request, "No active shift found.")
        return redirect('guard-dashboard')
    
    # Get handover note from form
    handover_note = request.POST.get('handover_note', '').strip()
    
    # Create handover note if provided
    if handover_note:
        note = GuardNotesManager.create_note(
            guard=request.user,
            content=handover_note,
            priority='normal',
            shift=shift
        )
    
    # Update shift with end time
    shift.shift_end = timezone.now()
    shift.save()
    
    # Calculate shift summary
    shift_metrics = GuardPerformanceTracker.get_shift_metrics(shift)
    
    # Log shift end
    GuardActivityLogger.log_shift_action(
        guard=request.user,
        action='shift_end',
        shift=shift,
        notes=handover_note
    )
    
    # Render shift summary
    context = {
        'shift': shift,
        'metrics': shift_metrics,
        'handover_note': handover_note
    }
    
    return render(request, 'gate/shift_summary.html', context)


@login_required
def quick_student_lookup_view(request):
    """
    AJAX endpoint for quick student lookup.
    """
    if not _is_guard(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    
    # Validate query length
    if len(query) < 3:
        return JsonResponse({
            'success': False,
            'error': 'Search query must be at least 3 characters'
        }, status=400)
    
    # Try lookup by ID first
    student = StudentLookupService.lookup_by_id(query)
    
    if not student:
        # Try lookup by name
        students = StudentLookupService.lookup_by_name(query, limit=10)
        
        if students.count() == 0:
            # Log lookup
            GuardActivityLogger.log_lookup(
                guard=request.user,
                query=query,
                results_count=0,
                device_id=request.GET.get('device_id', ''),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': 'No students found'
            }, status=404)
        
        # Return multiple results
        results = []
        for s in students:
            results.append({
                'student_id': s.student_id,
                'name': s.get_full_name(),
                'course': s.course or '—',
                'year_level': s.year_level or '—'
            })
        
        # Log lookup
        GuardActivityLogger.log_lookup(
            guard=request.user,
            query=query,
            results_count=len(results),
            device_id=request.GET.get('device_id', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'multiple': True,
            'results': results
        })
    
    # Single student found - get detailed info
    today_schedule = StudentLookupService.get_today_schedule(student)
    recent_entries = StudentLookupService.get_recent_entries(student, days=3)
    
    # Build entry history
    entry_history = []
    for entry in recent_entries:
        entry_history.append({
            'timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M'),
            'scan_type': entry.scan_type or 'IN',
            'granted': entry.granted,
            'notes': entry.notes or ''
        })
    
    # Log lookup
    GuardActivityLogger.log_lookup(
        guard=request.user,
        query=query,
        results_count=1,
        device_id=request.GET.get('device_id', ''),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return JsonResponse({
        'success': True,
        'multiple': False,
        'student': {
            'student_id': student.student_id,
            'name': student.get_full_name(),
            'course': student.course or '—',
            'year_level': student.year_level or '—',
            'photo_url': student.face_photo.url if student.face_photo else None,
            'today_schedule': today_schedule,
            'recent_entries': entry_history
        }
    })


@login_required
def dashboard_stats_api_view(request):
    """
    AJAX endpoint for dashboard auto-refresh.
    """
    if not _is_guard(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Get current stats
    stats = RealtimeDashboardService.get_current_stats()
    
    # Convert datetime to string for JSON
    stats['timestamp'] = stats['timestamp'].isoformat()
    
    return JsonResponse({
        'success': True,
        'stats': stats
    })


@login_required
def check_new_notifications_api_view(request):
    """
    AJAX endpoint to check for new notifications since a given timestamp.
    Accessible to guards, admin, and staff.
    """
    # Allow guards, admin, and staff to check notifications
    if not (_is_guard(request.user) or _is_supervisor_or_admin(request.user)):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Only guards have GuardNotification, so check if user is guard
    if not _is_guard(request.user):
        # Non-guards get empty notification list
        return JsonResponse({
            'success': True,
            'notifications': []
        })
    
    since_str = request.GET.get('since', '')
    
    try:
        # Parse the since timestamp
        if since_str:
            since = timezone.datetime.fromisoformat(since_str.replace('Z', '+00:00'))
        else:
            # Default to last 1 minute
            since = timezone.now() - timedelta(minutes=1)
    except (ValueError, AttributeError):
        since = timezone.now() - timedelta(minutes=1)
    
    # Get unread notifications created after 'since'
    notifications = GuardNotification.objects.filter(
        target_guard=request.user,
        is_read=False,
        created_at__gt=since
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).order_by('-created_at')[:5]
    
    # Format notifications for JSON
    notification_list = []
    for notif in notifications:
        notification_list.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'priority': notif.priority,
            'created_at': notif.created_at.isoformat(),
        })
    
    return JsonResponse({
        'success': True,
        'notifications': notification_list
    })


@login_required
def guard_activity_log_view(request):
    """
    Guard activity log with filtering and pagination.
    """
    if not _is_guard(request.user):
        messages.error(request, "Access denied. Guard role required.")
        return redirect('home')
    
    # Check user role
    role = get_user_role(request.user)
    
    # Guards see own logs, supervisors see all
    if role == 'guard':
        logs = GuardActivityLog.objects.filter(guard=request.user)
    elif role in ('admin', 'supervisor'):
        logs = GuardActivityLog.objects.all()
    else:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Get filters
    action_type = request.GET.get('action_type', '')
    from_date_str = request.GET.get('from_date', '')
    to_date_str = request.GET.get('to_date', '')
    
    # Apply action type filter
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    # Apply date range filter
    if from_date_str:
        try:
            from_date = timezone.datetime.strptime(from_date_str, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            logs = logs.filter(timestamp__gte=from_date)
        except ValueError:
            pass
    
    if to_date_str:
        try:
            to_date = timezone.datetime.strptime(to_date_str, '%Y-%m-%d')
            to_date = timezone.make_aware(to_date) + timedelta(days=1)
            logs = logs.filter(timestamp__lt=to_date)
        except ValueError:
            pass
    
    # Order by timestamp descending
    logs = logs.select_related(
        'guard', 'related_entry', 'related_incident', 
        'related_shift', 'related_student'
    ).order_by('-timestamp')
    
    # Paginate (50 per page)
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get available action types for filter
    action_types = GuardActivityLog.objects.values_list(
        'action_type', flat=True
    ).distinct().order_by('action_type')
    
    context = {
        'logs': page_obj,
        'action_types': action_types,
        'selected_action_type': action_type,
        'from_date': from_date_str,
        'to_date': to_date_str,
    }
    
    return render(request, 'gate/guard_activity_log.html', context)



@login_required
def admin_send_guard_notification_view(request):
    """
    Admin view to send custom notifications to guards.
    """
    from django.contrib.auth.models import User
    
    # Check if user is admin or supervisor
    if not _is_supervisor_or_admin(request.user):
        messages.error(request, "Access denied. Admin or supervisor role required.")
        return redirect('home')
    
    if request.method == 'POST':
        # Get form data
        recipient_type = request.POST.get('recipient_type')  # all, on_duty, specific
        specific_guard_id = request.POST.get('specific_guard')
        priority = request.POST.get('priority', 'normal')
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        
        # Validate
        if not title or not message_text:
            messages.error(request, "Title and message are required.")
            return redirect('guard-activity')
        
        # Determine recipients
        if recipient_type == 'all':
            # All guards
            guards = User.objects.filter(groups__name='Guard')
            broadcast = True
        elif recipient_type == 'on_duty':
            # Only on-duty guards
            active_shifts = GuardShift.objects.filter(shift_end__isnull=True).select_related('guard')
            guards = [shift.guard for shift in active_shifts]
            broadcast = True
        elif recipient_type == 'specific' and specific_guard_id:
            # Specific guard
            try:
                guard = User.objects.get(id=specific_guard_id, groups__name='Guard')
                guards = [guard]
                broadcast = False
            except User.DoesNotExist:
                messages.error(request, "Selected guard not found.")
                return redirect('guard-activity')
        else:
            messages.error(request, "Invalid recipient selection.")
            return redirect('guard-activity')
        
        # Create notifications
        created_count = 0
        for guard in guards:
            GuardNotification.objects.create(
                notification_type='system',
                priority=priority,
                title=title,
                message=message_text,
                target_guard=guard,
                broadcast=broadcast
            )
            created_count += 1
        
        messages.success(request, f"Notification sent to {created_count} guard(s).")
        return redirect('guard-activity')
    
    # GET request - show form
    all_guards = User.objects.filter(groups__name='Guard').order_by('username')
    on_duty_count = GuardShift.objects.filter(shift_end__isnull=True).count()
    
    context = {
        'all_guards': all_guards,
        'on_duty_count': on_duty_count,
    }
    
    return render(request, 'gate/admin_send_guard_notification.html', context)
