from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.db import transaction
from django.utils import timezone

User = get_user_model()

from .models import (
    EventCategory,
    Event,
    JobCategory,
    EventJobCategoryLinking,
    EventMember,
    EventUserWishList,
    UserCoin,
    Student,
    StaffPersonnelProfile,
    GateEntry,
    GateIncident,
    GateShift,
    EventAttendance,
    EventRegistration,
    AttendanceLog,
    ScannerDevice,
    GeneratedReport,
    AuditLog,
    VisitorPass,
    VisitorVisit,
    VisitorEntry,
    StudentBlock,
    EventWaitlist,
    RecurringEventTemplate,
    SiteTheme,
    GatePolicy,
    BlockedIP,
)
from .admin_mixins import PerPageListMixin
from .audit import log_action
from .notifications import notify_student_status_change


@admin.register(Event)
class EventAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('name', 'venue', 'start_date', 'end_date', 'attendance_mode', 'event_location', 'status')
    list_filter = ('attendance_mode', 'event_location', 'status')
    list_editable = ('attendance_mode', 'event_location')


admin.site.register(EventCategory)
admin.site.register(JobCategory)
admin.site.register(EventJobCategoryLinking)
admin.site.register(EventMember)
admin.site.register(EventUserWishList)
admin.site.register(UserCoin)


@admin.register(StaffPersonnelProfile)
class StaffPersonnelProfileAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('user', 'department', 'position', 'contact_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'department', 'position')
    raw_id_fields = ('user',)


@admin.register(Student)
class StudentAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('student_id', 'get_full_name', 'sex', 'email', 'has_signature', 'is_active', 'created_at')
    search_fields = ('student_id', 'first_name', 'middle_name', 'last_name', 'email')
    list_filter = ('sex', 'is_active')
    actions = ['resend_approval_email']

    def has_signature(self, obj):
        return bool(obj.signature)
    has_signature.boolean = True
    has_signature.short_description = 'Signature'

    def resend_approval_email(self, request, queryset):
        sent = 0
        for student in queryset.filter(account_status=Student.ACCOUNT_STATUS_APPROVED).exclude(email__isnull=True).exclude(email=''):
            try:
                notify_student_status_change(student, new_status=Student.ACCOUNT_STATUS_APPROVED)
                sent += 1
            except Exception:
                pass
        self.message_user(request, f'Approval email sent to {sent} student(s).')
    resend_approval_email.short_description = 'Resend approval email'


    def save_model(self, request, obj, form, change):
        """
        Ensure student approval via Django admin behaves like the custom views:
        - When account_status changes to APPROVED, set is_active=True, approved_by/approved_at.
        - Send the student an email about the new status.
        """
        old_status = None
        if change and obj.pk:
            try:
                old_status = Student.objects.only('account_status').get(pk=obj.pk).account_status
            except Student.DoesNotExist:
                old_status = None

        super().save_model(request, obj, form, change)

        new_status = obj.account_status
        if new_status == Student.ACCOUNT_STATUS_APPROVED and old_status != Student.ACCOUNT_STATUS_APPROVED:
            # Sync approval metadata
            if not obj.approved_at:
                obj.approved_at = timezone.now()
            if not obj.approved_by_id:
                obj.approved_by = request.user
            if not obj.is_active:
                obj.is_active = True
            obj.save(update_fields=['approved_by', 'approved_at', 'is_active'])
            log_action(
                request,
                'student_approved_admin',
                'Student',
                object_id=obj.pk,
                description=f'Student {obj.student_id} approved via Django admin',
            )
        elif new_status == Student.ACCOUNT_STATUS_INACTIVE and old_status != Student.ACCOUNT_STATUS_INACTIVE:
            if obj.is_active:
                obj.is_active = False
                obj.save(update_fields=['is_active'])
            log_action(
                request,
                'student_status_changed_admin',
                'Student',
                object_id=obj.pk,
                description=f'Student {obj.student_id} status set to {new_status} via Django admin',
            )

        # If status changed at all, notify the student (best-effort).
        if old_status is not None and new_status != old_status:
            try:
                notify_student_status_change(obj, new_status=new_status)
            except Exception:
                # Fail silently in admin, but keep the status change.
                pass


@admin.register(GateEntry)
class GateEntryAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('student', 'scan_type', 'result', 'granted', 'out_reason_code', 'out_reason', 'recorded_by', 'device_id', 'timestamp', 'incident')
    list_filter = ('granted', 'result', 'scan_type')
    search_fields = ('student__student_id', 'notes', 'out_reason', 'out_reason_code', 'device_id')
    date_hierarchy = 'timestamp'


@admin.register(GatePolicy)
class GatePolicyAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = (
        'name', 'gate_open_time', 'lunch_out_start', 'lunch_in_start', 'general_out_until',
        'strict_lunch_return', 'out_buffer_minutes',
        'permissive_college_mode', 'is_active',
    )


@admin.register(GateIncident)
class GateIncidentAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'student', 'scanned_id', 'reason', 'staff_alerted', 'timestamp', 'photo')
    list_filter = ('reason',)
    date_hierarchy = 'timestamp'


@admin.register(GateShift)
class GateShiftAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('personnel', 'shift_start', 'shift_end', 'gate_post', 'notes')
    list_filter = ('personnel',)
    date_hierarchy = 'shift_start'
    search_fields = ('personnel__username', 'gate_post', 'notes')


@admin.register(EventAttendance)
class EventAttendanceAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('student', 'event', 'participated', 'checked_in_at', 'checked_out_at', 'recorded_at')
    list_filter = ('participated', 'event')
    date_hierarchy = 'recorded_at'
    list_editable = ('participated',)
    actions = ['mark_as_present', 'mark_as_absent']

    def mark_as_present(self, request, queryset):
        n = queryset.update(participated=True)
        log_action(request, 'mark_present', 'EventAttendance', description=f'Marked {n} as present')
        self.message_user(request, f'{n} marked as present.')
    mark_as_present.short_description = 'Mark selected as present'

    def mark_as_absent(self, request, queryset):
        n = queryset.update(participated=False)
        log_action(request, 'mark_absent', 'EventAttendance', description=f'Marked {n} as absent')
        self.message_user(request, f'{n} marked as absent.')
    mark_as_absent.short_description = 'Mark selected as absent'


@admin.register(EventRegistration)
class EventRegistrationAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('student', 'event', 'status', 'checked_in_at', 'checked_out_at', 'issued_at')
    list_filter = ('status', 'event')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name', 'token')
    readonly_fields = ('token', 'issued_at')
    date_hierarchy = 'issued_at'


@admin.register(AttendanceLog)
class AttendanceLogAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('event', 'student', 'scan_type', 'result', 'scan_time', 'device_id', 'recorded_by', 'voided')
    list_filter = ('result', 'scan_type', 'event', 'voided')
    search_fields = ('student__student_id', 'token', 'remarks')
    readonly_fields = ('scan_time', 'client_scan_time')
    date_hierarchy = 'scan_time'
    list_editable = ('voided',)
    actions = ['void_selected_logs', 'unvoid_selected_logs']

    def void_selected_logs(self, request, queryset):
        n = queryset.filter(voided=False).update(
            voided=True, voided_at=timezone.now(), voided_by=request.user
        )
        log_action(request, 'void_logs', 'AttendanceLog', description=f'Voided {n} log(s)')
        self.message_user(request, f'{n} log(s) voided.')
    void_selected_logs.short_description = 'Void selected logs'

    def unvoid_selected_logs(self, request, queryset):
        n = queryset.filter(voided=True).update(
            voided=False, voided_at=None, voided_by=None
        )
        log_action(request, 'unvoid_logs', 'AttendanceLog', description=f'Unvoided {n} log(s)')
        self.message_user(request, f'{n} log(s) unvoided.')
    unvoid_selected_logs.short_description = 'Unvoid selected logs'


@admin.register(ScannerDevice)
class ScannerDeviceAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('device_id', 'name', 'location', 'is_active', 'last_seen_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('device_id', 'name', 'location')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)


@admin.register(GeneratedReport)
class GeneratedReportAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('title', 'report_type', 'period_start', 'period_end', 'generated_at', 'generated_by', 'has_file')
    list_filter = ('report_type',)
    date_hierarchy = 'generated_at'
    readonly_fields = ('generated_at',)
    search_fields = ('title',)

    def has_file(self, obj):
        return bool(obj.file)
    has_file.boolean = True
    has_file.short_description = 'File'


@admin.register(AuditLog)
class AuditLogAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('user', 'action', 'model_name', 'object_id', 'ip_address', 'created_at')
    list_filter = ('action',)
    date_hierarchy = 'created_at'
    search_fields = ('user__username', 'action', 'description')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'description', 'ip_address', 'created_at')


@admin.register(BlockedIP)
class BlockedIPAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('ip_address', 'reason', 'blocked_by', 'blocked_at', 'is_active', 'failed_attempts')
    list_filter = ('is_active',)
    search_fields = ('ip_address', 'reason')
    readonly_fields = ('blocked_at', 'failed_attempts')


@admin.register(VisitorPass)
class VisitorPassAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('code', 'status', 'guest_name', 'department', 'last_used_at', 'used_at', 'created_by')
    list_filter = ('status', 'used_at')
    search_fields = ('code', 'guest_name', 'purpose', 'department')


@admin.register(VisitorVisit)
class VisitorVisitAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('full_name', 'pass_obj', 'department', 'status', 'checked_in_at', 'checked_out_at', 'checked_in_by')
    list_filter = ('status', 'department')
    date_hierarchy = 'checked_in_at'
    search_fields = ('full_name', 'purpose', 'department')
    readonly_fields = ('checked_in_at', 'checked_out_at')


@admin.register(VisitorEntry)
class VisitorEntryAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('visitor_name', 'purpose', 'who_to_visit', 'recorded_by', 'timestamp', 'has_photo')
    list_filter = ('timestamp',)
    date_hierarchy = 'timestamp'
    search_fields = ('visitor_name', 'purpose', 'who_to_visit')
    readonly_fields = ('timestamp', 'photo')

    def has_photo(self, obj):
        return bool(obj.photo)
    has_photo.boolean = True
    has_photo.short_description = 'Photo'


@admin.register(StudentBlock)
class StudentBlockAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('student', 'reason', 'block_from', 'block_until', 'is_allowlist', 'created_by')
    list_filter = ('is_allowlist',)
    date_hierarchy = 'block_from'
    search_fields = ('student__student_id', 'reason')


@admin.register(EventWaitlist)
class EventWaitlistAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('event', 'student', 'position', 'created_at', 'promoted_at')
    list_filter = ('event',)
    date_hierarchy = 'created_at'


@admin.register(RecurringEventTemplate)
class RecurringEventTemplateAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('name', 'recurrence', 'day_of_week', 'day_of_month', 'is_active', 'last_generated')
    list_filter = ('recurrence', 'is_active')


@admin.register(SiteTheme)
class SiteThemeAdmin(PerPageListMixin, admin.ModelAdmin):
    list_per_page = 10
    list_display = ('site_name', 'primary_color', 'default_first_signatory_name', 'default_second_signatory_name', 'updated_at')


# Audit role (groups) changes in app View logs. Groups are saved in save_related, not save_model.
if User is not None:
    try:
        admin.site.unregister(User)
    except admin.sites.NotRegistered:
        pass

    class UserAdminWithAudit(PerPageListMixin, AuthUserAdmin):
        list_per_page = 10

        def formfield_for_manytomany(self, db_field, request, **kwargs):
            """
            Show model verbose names in the user permissions picker instead of internal
            names like ``gateshift`` (ContentType.model).
            """
            formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
            if db_field.name == 'user_permissions' and formfield is not None:

                def label_from_instance(obj):
                    ct = obj.content_type
                    model = ct.model_class()
                    if model is not None:
                        label = str(model._meta.verbose_name)
                    else:
                        label = ct.model.replace('_', ' ')
                    return '%s | %s | %s' % (ct.app_label, label, obj.name)

                formfield.label_from_instance = label_from_instance
            return formfield

        def save_related(self, request, form, formsets, change):
            obj = form.instance
            old_groups = set(obj.groups.values_list('name', flat=True)) if obj.pk else set()
            super().save_related(request, form, formsets, change)
            if obj.pk:
                new_groups = set(obj.groups.values_list('name', flat=True))
                if old_groups != new_groups:
                    # Log after commit so a failed AuditLog row cannot poison the same atomic block as auth M2M.
                    desc = '%s: %s → %s' % (
                        obj.username,
                        ', '.join(sorted(old_groups)) or '—',
                        ', '.join(sorted(new_groups)) or '—',
                    )

                    def _log_role_change():
                        log_action(
                            request, 'role_change', 'User',
                            object_id=obj.pk,
                            description=desc,
                        )

                    transaction.on_commit(_log_role_change)

    admin.site.register(User, UserAdminWithAudit)
