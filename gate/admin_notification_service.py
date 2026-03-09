"""
Admin Notification Service
Handles creation and management of admin/staff notifications.
"""
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from .models import AdminNotification


class AdminNotificationService:
    """
    Service for creating and managing admin notifications.
    """
    
    @staticmethod
    def create_notification(notification_type, title, message, priority='normal', 
                          target_user=None, broadcast=False, **kwargs):
        """
        Create a new admin notification.
        
        Args:
            notification_type: Type of notification (student_registration, incident, etc.)
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, high, urgent)
            target_user: Specific user to notify (None if broadcast)
            broadcast: Send to all admins/staff
            **kwargs: Additional fields (related_student, related_incident, etc.)
        
        Returns:
            AdminNotification object or list of objects if broadcast
        """
        if broadcast:
            # Send to all admins and staff
            admin_staff_users = User.objects.filter(
                groups__name__in=['Admin', 'Staff', 'Supervisor']
            ).distinct()
            
            notifications = []
            for user in admin_staff_users:
                notif = AdminNotification.objects.create(
                    notification_type=notification_type,
                    priority=priority,
                    title=title,
                    message=message,
                    target_user=user,
                    broadcast=True,
                    related_student=kwargs.get('related_student'),
                    related_incident=kwargs.get('related_incident'),
                    related_event=kwargs.get('related_event'),
                    related_entry=kwargs.get('related_entry'),
                    expires_at=kwargs.get('expires_at'),
                )
                notifications.append(notif)
            return notifications
        else:
            # Send to specific user
            return AdminNotification.objects.create(
                notification_type=notification_type,
                priority=priority,
                title=title,
                message=message,
                target_user=target_user,
                broadcast=False,
                related_student=kwargs.get('related_student'),
                related_incident=kwargs.get('related_incident'),
                related_event=kwargs.get('related_event'),
                related_entry=kwargs.get('related_entry'),
                expires_at=kwargs.get('expires_at'),
            )
    
    @staticmethod
    def notify_student_registration(student):
        """
        Notify admins when a new student registers.
        """
        return AdminNotificationService.create_notification(
            notification_type='student_registration',
            title='New Student Registration',
            message=f'{student.get_full_name()} ({student.student_id}) has registered and is pending approval.',
            priority='normal',
            broadcast=True,
            related_student=student,
        )
    
    @staticmethod
    def notify_incident(incident, priority='high'):
        """
        Notify admins when an incident is reported.
        """
        reason_display = dict(incident.REASON_CHOICES).get(incident.reason, incident.reason)
        student_info = incident.student.get_full_name() if incident.student else incident.scanned_id
        
        return AdminNotificationService.create_notification(
            notification_type='incident',
            title='Security Incident Reported',
            message=f'Incident: {reason_display} - {student_info}',
            priority=priority,
            broadcast=True,
            related_incident=incident,
        )
    
    @staticmethod
    def notify_capacity_alert(current_count, capacity_percent):
        """
        Notify admins when campus capacity reaches threshold.
        """
        return AdminNotificationService.create_notification(
            notification_type='capacity',
            title='Campus Capacity Alert',
            message=f'Campus is at {capacity_percent}% capacity ({current_count} people inside).',
            priority='high' if capacity_percent >= 90 else 'normal',
            broadcast=True,
        )
    
    @staticmethod
    def notify_guard_alert(guard, alert_message, priority='normal'):
        """
        Notify admins about guard-related alerts.
        """
        guard_name = guard.get_full_name() or guard.username
        
        return AdminNotificationService.create_notification(
            notification_type='guard_alert',
            title=f'Guard Alert: {guard_name}',
            message=alert_message,
            priority=priority,
            broadcast=True,
        )
    
    @staticmethod
    def get_unread_notifications(user):
        """
        Get all unread notifications for a user.
        """
        now = timezone.now()
        return AdminNotification.objects.filter(
            target_user=user,
            is_read=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).order_by('-created_at')
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of notification
            user: User object (must be the target_user)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = AdminNotification.objects.get(
                id=notification_id,
                target_user=user
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            return True
        except AdminNotification.DoesNotExist:
            return False
