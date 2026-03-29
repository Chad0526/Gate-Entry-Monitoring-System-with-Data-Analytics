"""
Admin Notification Service
In-app notifications + email via gate.notifications.send_announcement_emails.
"""
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from .models import AdminNotification


class AdminNotificationService:
    """Broadcast audiences are chosen by notification_type (see _broadcast_user_query)."""

    @staticmethod
    def _broadcast_user_query(notification_type):
        """
        Who receives broadcast AdminNotifications + matching emails:
        - incident, student_registration: Admin + Student Affairs
        - staff_personnel_registration, personnel_alert: Admin + superusers (account approval)
        - capacity: Admin + Student Affairs (campus ops)
        - default: Admin + Staff + Faculty (general announcements)
        """
        admin = Q(groups__name__iexact='admin')
        sas = Q(groups__name__iexact='Student Affairs')
        staff = Q(groups__name__iexact='staff')
        faculty = Q(groups__name__iexact='faculty')
        su = Q(is_superuser=True)
        if notification_type in ('incident', 'student_registration'):
            return admin | sas
        if notification_type in ('staff_personnel_registration', 'personnel_alert'):
            return admin | su
        if notification_type == 'capacity':
            return admin | sas
        return admin | staff | faculty

    @staticmethod
    def create_notification(notification_type, title, message, priority='normal',
                          target_user=None, broadcast=False, **kwargs):
        """
        Create a new admin notification.
        When broadcast=True, recipients follow _broadcast_user_query(notification_type).
        Email uses send_announcement_emails (Staff opt-in; Admin/SAS use User.email when set).
        """
        if broadcast:
            q = AdminNotificationService._broadcast_user_query(notification_type)
            broadcast_users = User.objects.filter(q).filter(is_active=True).distinct()

            notifications = []
            for user in broadcast_users:
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
        Notify Admin and Student Affairs when a new student self-registers (inactive until approved).
        """
        return AdminNotificationService.create_notification(
            notification_type='student_registration',
            title='New student registration',
            message=(
                f'{student.get_full_name()} ({student.student_id}) registered online and needs activation '
                f'when records are verified.'
            ),
            priority='normal',
            broadcast=True,
            related_student=student,
        )

    @staticmethod
    def notify_staff_personnel_registration(user, role_display):
        """
        Notify admins when a new staff/faculty/student affairs user registers (pending approval).
        """
        name = user.get_full_name() or user.username
        return AdminNotificationService.create_notification(
            notification_type='staff_personnel_registration',
            title='New Staff/Faculty/Student Affairs Registration',
            message=f'{name} ({user.username}) has registered as {role_display} and is pending approval. Activate the account in Admin → Users.',
            priority='normal',
            broadcast=True,
        )
    
    @staticmethod
    def notify_incident(incident, priority='high'):
        """
        Notify Admin and Student Affairs (SAS) when a gate incident is recorded (e.g. ID mismatch).
        Staff and faculty are not notified.
        """
        from django.urls import reverse
        reason_display = dict(incident.REASON_CHOICES).get(incident.reason, incident.reason)
        student_info = incident.student.get_full_name() if incident.student else (incident.scanned_id or '—')
        try:
            list_path = reverse('gate-incident-list')
        except Exception:
            list_path = '/gate/incidents/'
        body = (
            f'Incident: {reason_display} — {student_info}\n'
            f'Details: {(incident.details or "—")[:500]}\n'
            f'Log: {list_path}'
        )
        return AdminNotificationService.create_notification(
            notification_type='incident',
            title=f'Gate incident: {reason_display}',
            message=body[:1000],
            priority=priority,
            broadcast=True,
            related_incident=incident,
        )

    @staticmethod
    def notify_admins_inactive_student_sas_verified(incident, student, sas_user):
        """
        Notify Admin-group users that Student Affairs marked the incident checked for a student
        whose account is still inactive, so the account may be activated.
        """
        from django.urls import reverse

        try:
            list_path = reverse('gate-incident-list')
        except Exception:
            list_path = '/gate/incidents/'
        try:
            student_edit_path = reverse('gate-student-edit', kwargs={'pk': student.pk})
        except Exception:
            student_edit_path = ''
        sas_name = sas_user.get_full_name() or sas_user.username
        st_name = student.get_full_name()
        st_id = student.student_id
        title = f'Ready to activate: {st_id}'
        message = (
            f'Student Affairs ({sas_name}) marked the gate incident as checked for {st_name} ({st_id}). '
            f'The student was consulted and is cleared; the account is still inactive — activate when appropriate.\n'
            f'Details: {(incident.details or "—")[:400]}\n'
            f'Incidents: {list_path}'
        )
        if student_edit_path:
            message += f'\nStudent (app): {student_edit_path}'
        message = message[:1000]

        admin_q = Q(groups__name__iexact='admin') | Q(is_superuser=True)
        admin_users = User.objects.filter(admin_q).distinct()
        notifications = []
        for user in admin_users:
            notifications.append(
                AdminNotificationService.create_notification(
                    notification_type='sas_inactive_ready_activation',
                    title=title[:200],
                    message=message,
                    priority='normal',
                    target_user=user,
                    broadcast=False,
                    related_student=student,
                    related_incident=incident,
                )
            )
        return notifications

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
    def notify_personnel_alert(user, alert_message, priority='normal'):
        """
        Notify admins about personnel/gate-related alerts.
        """
        display_name = user.get_full_name() or user.username

        return AdminNotificationService.create_notification(
            notification_type='personnel_alert',
            title=f'Personnel alert: {display_name}',
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
