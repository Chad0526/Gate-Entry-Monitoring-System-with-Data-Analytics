"""
Admin Notification Service
Handles creation and management of admin/staff/guard/faculty notifications.
In-app notifications + email to staff/guard/faculty who opted in (email_notifications_announcements).
"""
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from .models import AdminNotification, GuardNotification


class AdminNotificationService:
    """
    Service for creating and managing admin notifications.
    Broadcast includes staff, faculty, and guards (in-app + email when opted in).
    """
    
    @staticmethod
    def create_notification(notification_type, title, message, priority='normal', 
                          target_user=None, broadcast=False, **kwargs):
        """
        Create a new admin notification.
        When broadcast=True: notifies admin, staff, supervisor, faculty (AdminNotification),
        and guards (GuardNotification), then sends email to all who have
        email_notifications_announcements=True and an email address.
        
        Args:
            notification_type: Type of notification (student_registration, incident, etc.)
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, high, urgent)
            target_user: Specific user to notify (None if broadcast)
            broadcast: Send to all admins/staff/faculty/guards
            **kwargs: Additional fields (related_student, related_incident, etc.)
        
        Returns:
            AdminNotification object or list of objects if broadcast
        """
        if broadcast:
            # Include admin, staff, supervisor, faculty, and guard so everyone gets in-app + optional email
            broadcast_users = User.objects.filter(
                Q(groups__name__iexact='admin') |
                Q(groups__name__iexact='staff') |
                Q(groups__name__iexact='supervisor') |
                Q(groups__name__iexact='faculty') |
                Q(groups__name__iexact='guard')
            ).distinct()
            
            notifications = []
            guard_priority = 'urgent' if priority == 'urgent' else 'high' if priority == 'high' else 'medium' if priority == 'normal' else 'low'
            guard_type_choices = dict(GuardNotification.NOTIFICATION_TYPE_CHOICES)
            guard_notification_type = notification_type if notification_type in guard_type_choices else 'system'
            for user in broadcast_users:
                if user.groups.filter(name__iexact='guard').exists():
                    # Guards see GuardNotification in their navbar
                    notif = GuardNotification.objects.create(
                        notification_type=guard_notification_type,
                        priority=guard_priority,
                        title=title,
                        message=message,
                        target_guard=user,
                        broadcast=True,
                        related_incident=kwargs.get('related_incident'),
                        related_event=kwargs.get('related_event'),
                        related_entry=kwargs.get('related_entry'),
                        expires_at=kwargs.get('expires_at'),
                    )
                else:
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

            # Email announcement to all broadcast recipients who opted in (staff/guard/faculty)
            try:
                from .notifications import send_announcement_emails
                send_announcement_emails(broadcast_users, title, message)
            except Exception:
                pass
            return notifications
        else:
            # Send to specific user
            notif = AdminNotification.objects.create(
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
            # Optional: send email to this single user if they opted in
            if target_user:
                try:
                    from .notifications import send_announcement_emails
                    send_announcement_emails([target_user], title, message)
                except Exception:
                    pass
            return notif
    
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
    def notify_staff_guard_registration(user, role_display):
        """
        Notify admins when a new staff/faculty/guard registers (pending approval).
        """
        name = user.get_full_name() or user.username
        return AdminNotificationService.create_notification(
            notification_type='staff_guard_registration',
            title='New Staff/Faculty/Guard Registration',
            message=f'{name} ({user.username}) has registered as {role_display} and is pending approval. Activate the account in Admin → Users.',
            priority='normal',
            broadcast=True,
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
