"""
Admin Notification Service
In-app notifications + email via gate.notifications.send_announcement_emails.
"""
import logging

from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from .models import AdminNotification

logger = logging.getLogger(__name__)


class AdminNotificationService:
    """Broadcast audiences are chosen by notification_type (see _broadcast_user_query)."""

    @staticmethod
    def _broadcast_users_incident_or_student_reg():
        """
        Recipients for incident + student_registration broadcasts.
        Must match who the app treats as admin or SAS (see gate_analytics.roles.get_user_role):
        users in Admin / Student Affairs groups, superusers, and is_staff users with no other
        role group (get_user_role fallback → 'admin') — those were previously missing from Q-only queries.
        """
        from gate_analytics.roles import get_user_role

        recipients = {}
        qs = (
            User.objects.filter(is_active=True)
            .filter(
                Q(groups__name__iexact='admin')
                | Q(groups__name__iexact='Student Affairs')
                | Q(is_superuser=True)
                | Q(is_staff=True)
            )
            .distinct()
            .prefetch_related('groups')
        )
        for u in qs:
            role = get_user_role(u)
            if u.is_superuser or role in ('admin', 'student affairs'):
                recipients[u.pk] = u
        return list(recipients.values())

    @staticmethod
    def _users_app_admin_portal():
        """
        Users who should receive admin-only in-app rows (manual gate referral, SAS→admin heads-up).
        Superusers always; others only if get_user_role is 'admin' (includes is_staff fallback).
        """
        from gate_analytics.roles import get_user_role

        recipients = {}
        qs = (
            User.objects.filter(is_active=True)
            .filter(
                Q(groups__name__iexact='admin')
                | Q(is_superuser=True)
                | Q(is_staff=True)
            )
            .distinct()
            .prefetch_related('groups')
        )
        for u in qs:
            if u.is_superuser or get_user_role(u) == 'admin':
                recipients[u.pk] = u
        return list(recipients.values())

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
            return admin | sas | su
        if notification_type in ('staff_personnel_registration', 'personnel_alert'):
            return admin | su
        if notification_type == 'capacity':
            return admin | sas
        return admin | staff | faculty

    @staticmethod
    def create_notification(notification_type, title, message, priority='normal',
                          target_user=None, broadcast=False, send_email=True, **kwargs):
        """
        Create a new admin notification.
        When broadcast=True, recipients follow _broadcast_user_query(notification_type).
        Email uses send_announcement_emails (Staff opt-in; Admin/SAS use User.email when set).
        Set send_email=False to skip email (e.g. paired with another notification that already emailed).
        """
        if broadcast:
            if notification_type in ('incident', 'student_registration'):
                broadcast_users = AdminNotificationService._broadcast_users_incident_or_student_reg()
            else:
                q = AdminNotificationService._broadcast_user_query(notification_type)
                broadcast_users = list(
                    User.objects.filter(q).filter(is_active=True).distinct()
                )
            if not broadcast_users:
                logger.warning(
                    'AdminNotification broadcast skipped: zero recipients (type=%s, title=%s)',
                    notification_type,
                    title[:80],
                )

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

            if send_email:
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
            if target_user and send_email:
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
            title=f'New student: {student.student_id}',
            message=(
                f'{student.get_full_name()} ({student.student_id}) — self-registered; verify records, then activate.'
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
            title=f'Pending signup: {user.username}',
            message=f'{name} ({user.username}) — {role_display}, pending approval (Admin → Users).',
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
        det = (incident.details or '—').strip() or '—'
        body = (
            f'{reason_display} • {student_info}\n'
            f'Note: {det[:220]}{"…" if len(det) > 220 else ""}\n'
            f'{list_path}'
        )
        return AdminNotificationService.create_notification(
            notification_type='incident',
            title=f'Incident: {reason_display}',
            message=body[:1000],
            priority=priority,
            broadcast=True,
            related_incident=incident,
        )

    @staticmethod
    def notify_admins_sas_verified_incident(incident, student, sas_user):
        """
        When Student Affairs marks a gate incident as checked: notify app admins.
        Inactive accounts: prompt activation; already-active accounts: confirm resolved (audit).
        """
        from django.urls import reverse
        from .models import Student

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
        needs_activation = (
            student.account_status == Student.ACCOUNT_STATUS_INACTIVE or not student.is_active
        )
        note = (incident.details or '—').strip() or '—'
        if len(note) > 200:
            note = note[:200] + '…'
        if needs_activation:
            ntype = 'sas_inactive_ready_activation'
            title = f'SAS verified — {st_id}'
            message = (
                f'SAS ({sas_name}) completed follow-up for {st_name} ({st_id}) after the gate incident. '
                f'Open the student profile to set the account to Active if access should be enabled.\n'
                f'Note: {note}\n'
                f'{list_path}'
            )
            send_mail = True
        else:
            ntype = 'sas_verified_gate_followup'
            title = f'SAS cleared: {st_id} (active)'
            message = (
                f'SAS ({sas_name}) cleared {st_name} ({st_id}). Account already active — FYI only.\n'
                f'Note: {note}\n'
                f'{list_path}'
            )
            send_mail = False
        if student_edit_path:
            message += f'\n{student_edit_path}'
        message = message[:1000]

        admin_users = AdminNotificationService._users_app_admin_portal()
        notifications = []
        for user in admin_users:
            notifications.append(
                AdminNotificationService.create_notification(
                    notification_type=ntype,
                    title=title[:200],
                    message=message,
                    priority='normal' if not needs_activation else 'high',
                    target_user=user,
                    broadcast=False,
                    send_email=send_mail,
                    related_student=student,
                    related_incident=incident,
                )
            )
        return notifications

    @staticmethod
    def notify_admins_inactive_student_sas_verified(incident, student, sas_user):
        """Backward-compatible alias for notify_admins_sas_verified_incident."""
        return AdminNotificationService.notify_admins_sas_verified_incident(
            incident, student, sas_user
        )

    @staticmethod
    def notify_admins_gate_manual_referral(student, actor, office_label, related_incident=None):
        """
        In-app-only alerts for Admin (+ superusers): guard used manual entry with office routing.
        Message includes student edit URL so admins can set inactive if SAS has not resolved the case.
        """
        from django.urls import reverse

        if not student:
            return []
        actor_name = (
            (actor.get_full_name() if actor else '')
            or (getattr(actor, 'username', None) if actor else '')
            or 'Gate staff'
        )
        label = (office_label or 'Office referral').strip()[:200]
        try:
            st_path = reverse('gate-student-edit', kwargs={'pk': student.pk})
        except Exception:
            st_path = ''
        try:
            list_path = reverse('gate-incident-list')
        except Exception:
            list_path = '/gate/incidents/'
        st_name = student.get_full_name()
        st_id = student.student_id
        title = f'Manual entry: {label[:100]}'
        message = (
            f'{st_name} ({st_id}) • Route: {label}\n'
            f'By: {actor_name}\n'
            f'Unresolved? You may mark inactive from the student profile.\n'
        )
        if st_path:
            message += f'{st_path}\n'
        message += f'{list_path}\n'
        message = message[:1000]

        admin_users = AdminNotificationService._users_app_admin_portal()
        if not admin_users:
            logger.warning(
                'notify_admins_gate_manual_referral: no app-admin users to notify (student=%s)',
                student.pk,
            )
        notifications = []
        for user in admin_users:
            notifications.append(
                AdminNotificationService.create_notification(
                    notification_type='gate_manual_referral',
                    title=title[:200],
                    message=message,
                    priority='high',
                    target_user=user,
                    broadcast=False,
                    send_email=False,
                    related_student=student,
                    related_incident=related_incident,
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
