import datetime
from django.db import models
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


class EventCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=6, unique=True)
    image = models.ImageField(upload_to='event_category/', blank=True, null=True)
    priority = models.IntegerField(unique=True)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('event-category-list')

class JobCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    """Event with unified status (no separate scheduled_status). Audit uses DateTimeField."""
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    uid = models.PositiveIntegerField(unique=True, null=True, blank=True, help_text='Auto-generated if blank')
    description = RichTextUploadingField(blank=True)
    job_category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField()
    points = models.PositiveIntegerField(blank=True, null=True)
    capacity_alert_sent_at = models.DateTimeField(null=True, blank=True, help_text='When 80%% capacity alert was last sent')
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_updated_user')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    # Single status (replaces scheduled_status + old status)
    STATUS_CHOICES = (
        ('draft', 'Draft (not scheduled)'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Attendance: always taken by scanning student permanent eEID (Events → Attendance Scanner).
    # OPEN/SECURE is legacy; in practice all events use student QR only (no event-specific token required).
    ATTENDANCE_MODE_CHOICES = (
        ('OPEN', 'Open (Student eEID accepted)'),
        ('SECURE', 'Secure (legacy token option; student eEID still works)'),
    )
    attendance_mode = models.CharField(
        max_length=10,
        choices=ATTENDANCE_MODE_CHOICES,
        default='OPEN',
        help_text='Attendance is taken by scanning student eEID at Events → Attendance Scanner. OPEN is recommended.'
    )

    # On-campus vs field trip: display/categorization only. Both use the same scanner (student eEID).
    EVENT_LOCATION_CHOICES = (
        ('on_campus', 'On campus'),
        ('field_trip', 'Field trip / Off-campus'),
    )
    event_location = models.CharField(
        max_length=20,
        choices=EVENT_LOCATION_CHOICES,
        default='on_campus',
        help_text='Display only. Attendance for both types is taken via Events → Attendance Scanner (student eEID).'
    )

    # Audience targeting: who is expected/allowed to attend this event.
    AUDIENCE_SCOPE_CHOICES = (
        ('all', 'All students'),
        ('course', 'By program'),
        ('year_level', 'By year level'),
        ('course_year', 'By program + year level'),
        ('course_section', 'By program + section'),
        ('course_section_year', 'By program + section + year level'),
        ('specific_students', 'Specific students (registration list)'),
    )
    audience_scope = models.CharField(
        max_length=30,
        choices=AUDIENCE_SCOPE_CHOICES,
        default='all',
        help_text='Target audience for this event. Scanner checks student eligibility based on this rule.'
    )
    audience_course = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Audience program',
        help_text='Required when audience is by program / program+year / program+section / program+section+year.',
    )
    audience_year_level = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text='Required when audience is by year level / program+year / program+section+year.',
    )
    audience_section = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Required when audience is by program+section / program+section+year.',
    )

    def audience_matches_student(self, student):
        """Return True when the student belongs to this event's configured audience."""
        if student is None:
            return False
        scope = (self.audience_scope or 'all').strip().lower()
        if scope == 'all':
            return True

        student_course = (getattr(student, 'course', '') or '').strip().lower()
        student_year = (getattr(student, 'year_level', '') or '').strip()
        student_section = (getattr(student, 'section', '') or '').strip().lower()

        target_course = (self.audience_course or '').strip().lower()
        target_year = (self.audience_year_level or '').strip()
        target_section = (self.audience_section or '').strip().lower()

        if scope == 'course':
            return bool(target_course) and student_course == target_course
        if scope == 'year_level':
            return bool(target_year) and student_year == target_year
        if scope == 'course_year':
            return bool(target_course and target_year) and student_course == target_course and student_year == target_year
        if scope == 'course_section':
            return bool(target_course and target_section) and student_course == target_course and student_section == target_section
        if scope == 'course_section_year':
            return bool(target_course and target_section and target_year) and student_course == target_course and student_section == target_section and student_year == target_year
        # specific_students is validated using EventRegistration in scanner/views.
        return True

    def audience_summary(self):
        """Human-readable audience summary for UI/report pages."""
        scope = (self.audience_scope or 'all').strip().lower()
        if scope == 'all':
            return 'All students'
        if scope == 'course':
            return f'Program: {self.audience_course or "—"}'
        if scope == 'year_level':
            return f'Year level: {self.audience_year_level or "—"}'
        if scope == 'course_year':
            return f'Program + Year: {self.audience_course or "—"} / {self.audience_year_level or "—"}'
        if scope == 'course_section':
            return f'Program + Section: {self.audience_course or "—"} / {self.audience_section or "—"}'
        if scope == 'course_section_year':
            return f'Program + Section + Year: {self.audience_course or "—"} / {self.audience_section or "—"} / {self.audience_year_level or "—"}'
        if scope == 'specific_students':
            return 'Specific students (registration list)'
        return self.get_audience_scope_display()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event-list')

    def save(self, *args, **kwargs):
        if self.uid is None:
            from django.db.models import Max
            from django.db import transaction
            with transaction.atomic():
                max_uid = (
                    Event.objects.select_for_update()
                    .aggregate(Max('uid'))['uid__max']
                )
                self.uid = (max_uid or 0) + 1
                if self.points is None:
                    self.points = 0
                super().save(*args, **kwargs)
            return
        if self.points is None:
            self.points = 0
        super().save(*args, **kwargs)


class EventImage(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='event_image/', blank=True, null=True)


class EventAgenda(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    session_name = models.CharField(max_length=120, blank=True)
    speaker_name = models.CharField(max_length=120, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    venue_name = models.CharField(max_length=255, blank=True)


class EventJobCategoryLinking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    job_category = models.ForeignKey(JobCategory, on_delete=models.CASCADE)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return str(self.event)


class EventMember(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    attend_status_choice = (
        ('waiting', 'Waiting'),
        ('attending', 'Attending'),
        ('completed', 'Completed'),
        ('absent', 'Absent'),
        ('cancelled', 'Cancelled'),
    )
    attend_status = models.CharField(choices=attend_status_choice, max_length=10)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventmember_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventmember_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)


    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return str(self.user)
    
    def get_absolute_url(self):
        return reverse('join-event-list')


class EventUserWishList(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventwishlist_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventwishlist_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)


    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return str(self.event)
    
    def get_absolute_url(self):
        return reverse('event-wish-list')


class UserCoin(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    CHOICE_GAIN_TYPE = (
        ('event', 'Event'),
        ('others', 'Others'),
    )
    gain_type = models.CharField(max_length=6, choices=CHOICE_GAIN_TYPE)
    gain_coin = models.PositiveIntegerField()
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='usercoin_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='usercoin_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return str(self.user)
    
    def get_absolute_url(self):
        return reverse('user-mark')


# --- City College of Bayawan: Gate Access & Attendance Tracking ---

def student_photo_upload_to(instance, filename):
    """Store face photo under students/<student_id>/face.jpg for consistent gate verification."""
    ext = 'jpg'
    return f'students/{instance.student_id}/face.{ext}'


def student_signature_upload_to(instance, filename):
    """Store electronic signature under students/<student_id>/signature.png."""
    return f'students/{instance.student_id}/signature.png'


def normalize_student_name(value):
    """Return string with first letter of each word capitalized, rest lowercase (for admin/display)."""
    if value is None or not isinstance(value, str):
        return value
    s = (value or '').strip()
    if not s:
        return s
    return ' '.join(
        (w[0:1].upper() + w[1:].lower()) if w else ''
        for w in s.split()
    )


class Student(models.Model):
    """Student profile; QR code on ID embeds student_id for gate lookup."""

    # --- Account status ---
    ACCOUNT_STATUS_APPROVED = 'APPROVED'
    ACCOUNT_STATUS_ACTIVE = 'APPROVED'
    ACCOUNT_STATUS_INACTIVE = 'INACTIVE'
    ACCOUNT_STATUS_CHOICES = (
        ('APPROVED', 'Active'),
        ('INACTIVE', 'Inactive'),
    )
    account_status = models.CharField(
        max_length=10,
        choices=ACCOUNT_STATUS_CHOICES,
        default='APPROVED',
        db_index=True,
    )
    approved_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='students_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    # --- Core identity ---
    student_id = models.CharField(max_length=50, unique=True)  # Embedded in QR code
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Middle Initial')
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to=student_photo_upload_to, blank=True, null=True)
    signature = models.ImageField(upload_to=student_signature_upload_to, blank=True, null=True, help_text='Electronic signature from registration.')
    address = models.TextField(blank=True)
    birthdate = models.DateField(null=True, blank=True)
    SEX_MALE = 'MALE'
    SEX_FEMALE = 'FEMALE'
    SEX_CHOICES = (
        (SEX_MALE, 'Male'),
        (SEX_FEMALE, 'Female'),
    )
    sex = models.CharField(max_length=20, choices=SEX_CHOICES, blank=True, help_text='Sex/Gender')
    guardians_parents = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Guardian / Parent',
        help_text='Guardian(s) or parent(s) name(s)',
    )

    # --- Academic info (for analytics) ---
    COURSE_BST = 'BST'
    COURSE_BSE = 'BSE'
    COURSE_CHOICES = (
        ('BST', 'BST'),
        ('BSE', 'BSE'),
    )
    course = models.CharField(
        max_length=20,
        choices=COURSE_CHOICES,
        blank=True,
        verbose_name='Program',
    )
    section = models.CharField(max_length=20, blank=True)
    YEAR_LEVEL_CHOICES = (
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
    )
    year_level = models.CharField(max_length=50, choices=YEAR_LEVEL_CHOICES, blank=True, help_text='Year level for reports (1–4).')
    course_or_section = models.CharField(max_length=100, blank=True, help_text='Legacy: e.g. BSIT-A (for reports by program/section).')
    SEMESTER_TRANSITION_CLEAR = 'CLEAR'
    SEMESTER_TRANSITION_PENDING_SECOND_SEM = 'PENDING_SECOND_SEM'
    SEMESTER_TRANSITION_SECOND_SEM_CLEARED = 'SECOND_SEM_CLEARED'
    SEMESTER_TRANSITION_CHOICES = (
        (SEMESTER_TRANSITION_CLEAR, 'Clear / no semester hold'),
        (SEMESTER_TRANSITION_PENDING_SECOND_SEM, '1st semester completed - pending 2nd semester clearance'),
        (SEMESTER_TRANSITION_SECOND_SEM_CLEARED, '2nd semester cleared'),
    )
    semester_transition_status = models.CharField(
        max_length=30,
        choices=SEMESTER_TRANSITION_CHOICES,
        default=SEMESTER_TRANSITION_CLEAR,
        db_index=True,
        help_text='Set pending after 1st semester completion to block class entry until cleared for 2nd semester.',
    )
    office_clearance_hold = models.BooleanField(
        default=False,
        db_index=True,
        help_text='When true, student is blocked from gate entry until office issue is resolved.',
    )
    office_clearance_note = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Why the office clearance hold was applied.',
    )

    # --- Contacts ---
    contact_number = models.CharField(max_length=20, blank=True, verbose_name='Mobile number')
    guardian_contact = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Contact number',
        help_text='Emergency contact number (guardian).',
    )

    is_active = models.BooleanField(default=True)  # Gate access: True only when account_status=APPROVED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def save(self, *args, **kwargs):
        # Normalize text fields: first letter of each word capitalized, rest lowercase (registration/admin)
        self.first_name = normalize_student_name(self.first_name) or ''
        self.last_name = normalize_student_name(self.last_name) or ''
        if self.middle_name:
            self.middle_name = normalize_student_name(self.middle_name)
        if self.student_id:
            self.student_id = self.student_id.strip()
        if self.address:
            self.address = normalize_student_name(self.address)
        if self.guardians_parents:
            self.guardians_parents = normalize_student_name(self.guardians_parents)
        if self.section:
            self.section = normalize_student_name(self.section)
        if self.course_or_section:
            self.course_or_section = normalize_student_name(self.course_or_section)
        if self.sex and self.sex not in (self.SEX_MALE, self.SEX_FEMALE):
            self.sex = ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_id} - {self.get_full_name()}"

    def get_full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p).strip()

    def blocked_for_second_semester(self):
        return self.semester_transition_status == self.SEMESTER_TRANSITION_PENDING_SECOND_SEM

    def blocked_for_office_clearance(self):
        return bool(self.office_clearance_hold)


@receiver(pre_save, sender=Student)
def _student_store_previous_status(sender, instance, **kwargs):
    """
    Remember previous account_status so we can detect changes in post_save,
    no matter where the save came from (admin, custom views, shell, etc.).
    """
    if not instance.pk:
        instance._old_account_status = None
        return
    try:
        instance._old_account_status = sender.objects.only('account_status').get(pk=instance.pk).account_status
    except sender.DoesNotExist:
        instance._old_account_status = None


@receiver(post_save, sender=Student)
def _student_handle_status_change(sender, instance, created, **kwargs):
    """Keep is_active and approved_at in sync with account_status."""
    old_status = getattr(instance, '_old_account_status', None)
    new_status = instance.account_status
    if old_status == new_status:
        return

    update_fields = {}
    if new_status == Student.ACCOUNT_STATUS_APPROVED:
        if not instance.is_active:
            instance.is_active = True
            update_fields['is_active'] = True
        if not instance.approved_at:
            instance.approved_at = timezone.now()
            update_fields['approved_at'] = instance.approved_at
        if update_fields:
            sender.objects.filter(pk=instance.pk).update(**update_fields)
    elif new_status == Student.ACCOUNT_STATUS_INACTIVE:
        if instance.is_active:
            instance.is_active = False
            sender.objects.filter(pk=instance.pk).update(is_active=False)


class StaffPersonnelProfile(models.Model):
    """Extended profile for staff/faculty/personnel self-registrations (User + Group hold role)."""
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='staff_personnel_profile',
    )
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Middle Initial')
    SEX_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    )
    sex = models.CharField(max_length=20, choices=SEX_CHOICES, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=150, blank=True)
    position = models.CharField(max_length=150, blank=True)
    profile_complete = models.BooleanField(
        default=False,
        help_text='True after staff completes the required profile form after first login.',
    )
    # Preferences (staff/faculty/personnel)
    preferred_language = models.CharField(max_length=10, default='en', blank=True)
    preferred_timezone = models.CharField(max_length=63, default='Asia/Manila', blank=True)
    email_notifications_announcements = models.BooleanField(
        default=True,
        help_text='Receive email notifications for announcements.',
    )

    class Meta:
        verbose_name = 'Staff/Faculty/Personnel profile'
        verbose_name_plural = 'Staff/Faculty/Personnel profiles'

    def save(self, *args, **kwargs):
        allowed = {c[0] for c in self.SEX_CHOICES}
        if self.sex and self.sex not in allowed:
            self.sex = ''
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()} (Staff/Personnel)"


def user_profile_photo_upload_to(instance, filename):
    """Store profile photos under profile_photos/<user_id>/."""
    ext = (filename.split('.')[-1] if '.' in filename else 'jpg').lower()
    if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        ext = 'jpg'
    return f'profile_photos/{instance.user_id}/avatar.{ext}'


class UserProfile(models.Model):
    """Optional profile photo for any user (sidebar avatar)."""
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='user_profile',
    )
    avatar = models.ImageField(
        upload_to=user_profile_photo_upload_to,
        blank=True,
        null=True,
        help_text='Profile photo shown in the sidebar.',
    )

    def __str__(self):
        return f"Profile of {self.user.get_full_name() or self.user.username}"


class GateIncident(models.Model):
    """Record when entry is denied (e.g. identity mismatch); alert gate staff."""
    REASON_CHOICES = (
        ('identity_mismatch', 'Identity Mismatch'),
        ('invalid_id', 'Invalid or Expired ID'),
        ('not_registered', 'Not Registered'),
        ('proxy_attendance', 'Proxy Attendance'),
        ('other', 'Other'),
    )
    SAS_REVIEW_CHOICES = (
        ('to_check', 'To be checked'),
        ('verified', 'Verified by Student Affairs'),
    )
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    scanned_id = models.CharField(max_length=100, blank=True)  # What was scanned if no match
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default='identity_mismatch')
    details = models.TextField(blank=True)
    photo = models.ImageField(upload_to='incidents/', blank=True, null=True, help_text='Optional photo attached by gate staff')
    staff_alerted = models.BooleanField(
        default=True,
        verbose_name='Gate staff alerted',
        help_text='Whether gate personnel were notified about this incident.',
    )
    sas_review_status = models.CharField(
        max_length=20,
        choices=SAS_REVIEW_CHOICES,
        default='to_check',
        db_index=True,
        help_text='Student Affairs review status for ID mismatch follow-up.',
    )
    sas_checked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gate_incidents_checked',
        help_text='Student Affairs/admin user who verified this incident.',
    )
    sas_checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When Student Affairs marked this incident as verified.',
    )
    sas_check_notes = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Optional Student Affairs review note.',
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Incident {self.id} - {self.reason} @ {self.timestamp}"


class GateEntry(models.Model):
    """Each gate scan: IN/OUT, result, and optional out_reason_code for analytics. Audit: recorded_by = staff user."""
    SCAN_TYPE_CHOICES = (
        ('IN', 'IN'),
        ('OUT', 'OUT'),
    )
    RESULT_CHOICES = (
        ('SUCCESS', 'Success'),
        ('DENIED', 'Denied'),
        ('DUPLICATE', 'Duplicate'),
        ('BLOCKED', 'Blocked'),
        ('NOT_APPROVED', 'Not Approved'),
        ('NOT_FOUND', 'Not Found'),
    )
    OUT_REASON_CODE_CHOICES = (
        ('', '—'),
        ('NO_CLASS_WINDOW', 'No class / Schedule window'),
        ('LUNCH', 'Lunch break'),
        ('ALL_CLASSES_DONE', 'All classes done'),
        ('EMERGENCY', 'Emergency'),
        ('CLINIC', 'Clinic / Health'),
        ('OFFICIAL_BUSINESS', 'Official business'),
        ('OVERRIDE_BY_PERSONNEL', 'Override by staff'),
        ('OTHER', 'Other'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, help_text='Null when result=NOT_FOUND or visitor.')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_entries', help_text='Optional: if this scan is for tracking a specific college event.')
    visitor_visit = models.ForeignKey(
        'VisitorVisit', on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_entries',
        help_text='When set, this entry is visitor check-in/out (reusable pass lifecycle).',
    )
    granted = models.BooleanField(default=True)
    incident = models.OneToOneField(GateIncident, on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_entry')
    notes = models.TextField(blank=True)
    scan_type = models.CharField(max_length=3, choices=SCAN_TYPE_CHOICES, db_index=True, default='IN')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='SUCCESS', db_index=True)
    out_reason = models.TextField(
        blank=True,
        verbose_name='OUT note',
        help_text='Optional note when staff records OUT (e.g. override, lunch). Used in reports.',
    )
    out_reason_code = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text='Short code for analytics: LUNCH, NO_CLASS_WINDOW, OVERRIDE_BY_PERSONNEL, etc.',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_entries_recorded',
        help_text='Staff user who recorded this entry (audit trail).'
    )
    device_id = models.CharField(
        max_length=128, blank=True, default='',
        help_text='Scanner/terminal device ID (browser UUID from gate scan).'
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        help_text='Client IP when entry was recorded (audit).'
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Gate entries'
        permissions = [
            ('can_scan', 'Can scan at gate (IN/OUT)'),
            ('can_view_entries', 'Can view gate entries'),
            ('can_record_early_out', 'Can record early out / override'),
            ('can_report_proxy', 'Can report proxy attendance'),
        ]
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['scan_type', 'timestamp']),
            models.Index(fields=['student', 'timestamp']),
            models.Index(fields=['granted', 'timestamp']),  # dashboard/reports: granted today, denied today
        ]

    def __str__(self):
        sid = self.student.student_id if self.student else (self.notes or '?')
        return f"{sid} - {self.result} ({self.scan_type}) @ {self.timestamp}"


class GateShift(models.Model):
    """Lightweight shift record for gate accountability: who was on duty when."""
    personnel = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='gate_shifts',
        verbose_name='Personnel on duty',
        help_text='Personnel user on duty for this shift.',
    )
    shift_start = models.DateTimeField(help_text='Clock-in time.')
    shift_end = models.DateTimeField(null=True, blank=True, help_text='Clock-out time; null = still on duty.')
    gate_post = models.CharField(
        max_length=64, blank=True, default='',
        help_text='E.g. Main Gate, Back Gate (optional).'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-shift_start']
        verbose_name = 'Gate shift'
        verbose_name_plural = 'Gate shifts'
        indexes = [
            models.Index(fields=['personnel', '-shift_start']),
            models.Index(fields=['shift_start', 'shift_end']),
        ]

    def __str__(self):
        end = self.shift_end.strftime('%H:%M') if self.shift_end else 'ongoing'
        post = f' @ {self.gate_post}' if self.gate_post else ''
        return f"{self.personnel.get_full_name() or self.personnel.username}{post} {self.shift_start.strftime('%Y-%m-%d %H:%M')} – {end}"


class EventAttendance(models.Model):
    """Attendance for an event program: student participated or tagged as non-participant."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    participated = models.BooleanField(default=False)  # True = participated, False = non-participant
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text='When student checked in at event')
    checked_out_at = models.DateTimeField(null=True, blank=True, help_text='When student checked out from event')
    early_out_reason = models.TextField(max_length=500, blank=True, default='', help_text='Optional note when leaving the event before it ends')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'event']
        ordering = ['-recorded_at']
        verbose_name_plural = 'Event attendances'
        indexes = [
            models.Index(fields=['event', 'student']),
            models.Index(fields=['event', 'checked_in_at']),
        ]

    def __str__(self):
        return f"{self.student.student_id} @ {self.event.name} - {'Participated' if self.participated else 'Non-participant'}"


class EventRegistration(models.Model):
    """Token-based QR code for event attendance. Each student gets a unique token per event."""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('revoked', 'Revoked'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='event_registrations')
    token = models.CharField(max_length=64, unique=True, db_index=True, help_text='Unique token for QR code: EVT:<event_id>:<token>')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Check-in/out timestamps
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text='When student scanned IN at event')
    checked_out_at = models.DateTimeField(null=True, blank=True, help_text='When student scanned OUT at event')
    
    class Meta:
        unique_together = ['event', 'student']
        ordering = ['-issued_at']
        verbose_name_plural = 'Event registrations'
    
    def __str__(self):
        return f"{self.student.student_id} @ {self.event.name} ({self.status})"
    
    @staticmethod
    def generate_token():
        """Generate a secure random token for QR code."""
        import secrets
        return secrets.token_urlsafe(32)  # ~43 characters, URL-safe
    
    def get_qr_payload(self):
        """Returns the QR code text: EVT:<event_id>:<token>"""
        return f"EVT:{self.event.id}:{self.token}"


class AttendanceLog(models.Model):
    """Detailed log of every scan attempt for events (success/failure/duplicate/invalid)."""
    SCAN_TYPE_CHOICES = (
        ('IN', 'Check In'),
        ('OUT', 'Check Out'),
    )
    
    RESULT_CHOICES = (
        ('SUCCESS', 'Success'),
        ('DUPLICATE', 'Duplicate Scan'),
        ('INVALID', 'Invalid Token'),
        ('REVOKED', 'Token Revoked'),
        ('WRONG_EVENT', 'Wrong Event'),
        ('OUTSIDE_WINDOW', 'Outside Time Window'),
        ('NOT_CHECKED_IN', 'Check-out Before Check-in'),
        ('SECURE_EVENT_REQUIRES_TOKEN', 'Secure Event (Token Required)'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_logs')
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_logs')
    registration = models.ForeignKey(EventRegistration, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_logs')
    
    scan_time = models.DateTimeField(auto_now_add=True, help_text='Server time when scan was recorded')
    client_scan_time = models.DateTimeField(null=True, blank=True, help_text='Client device time (for offline scans)')
    scan_type = models.CharField(max_length=3, choices=SCAN_TYPE_CHOICES, default='IN')
    result = models.CharField(max_length=32, choices=RESULT_CHOICES)
    
    token = models.CharField(max_length=64, blank=True, default='', help_text='Token that was scanned')
    device_id = models.CharField(max_length=64, blank=True, default='', help_text='Scanner device identifier')
    remarks = models.CharField(max_length=255, blank=True, default='')
    recorded_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_logs_recorded',
        help_text='Staff user who recorded this scan (audit trail).'
    )
    voided = models.BooleanField(default=False, help_text='If True, this log entry was voided/corrected by admin.')
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_logs_voided',
        help_text='Admin who voided this log.'
    )
    
    class Meta:
        ordering = ['-scan_time']
        verbose_name_plural = 'Attendance logs'
        indexes = [
            models.Index(fields=['event', 'result', 'scan_time']),
            models.Index(fields=['student', 'scan_time']),
        ]
    
    def __str__(self):
        student_id = self.student.student_id if self.student else 'Unknown'
        return f"{student_id} @ {self.event.name} - {self.result} ({self.scan_type})"


class ScannerDevice(models.Model):
    """
    Registered scanner devices. When device management is enabled, only scans from
    registered active devices are accepted (optional security enhancement).
    """
    device_id = models.CharField(max_length=128, unique=True, help_text='UUID from scanner (localStorage scanner_device_id)')
    name = models.CharField(max_length=100, blank=True, help_text='Friendly name, e.g. "Gate A Tablet"')
    location = models.CharField(max_length=255, blank=True, help_text='Physical location, e.g. "Main Gate"')
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, auto_now_add=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['name', 'device_id']
        verbose_name = 'Scanner device'
        verbose_name_plural = 'Scanner devices'

    def __str__(self):
        return self.name or self.device_id


class GeneratedReport(models.Model):
    """Stored report metadata and optional file (daily/weekly/monthly scheduled or on-demand)."""
    REPORT_TYPE_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_demand', 'On-demand'),
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True, help_text='JSON: summary stats (counts, peak hours, etc.)')
    file = models.FileField(upload_to='reports/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_reports',
    )

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Generated report'
        verbose_name_plural = 'Generated reports'

    def __str__(self):
        return f"{self.get_report_type_display()} {self.period_start}–{self.period_end} ({self.generated_at.date()})"


class NotificationRead(models.Model):
    """
    Stores which navbar notifications a user has opened. Records are never deleted:
    once a notification is clicked it stays "read" (light style); only new ones appear highlighted.
    Persists across session resets and new student registrations.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notification_reads')
    notification_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'notification_key']]
        ordering = ['-created_at']
        verbose_name = 'Notification read'
        verbose_name_plural = 'Notification reads'

    def __str__(self):
        return f"{self.user.username}: {self.notification_key}"


# --------------- Extended features ---------------

class AuditLog(models.Model):
    """Who did what, when (admin/staff actions)."""
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=64, help_text='e.g. void_log, mark_present, deactivate_student')
    model_name = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Audit logs'

    def __str__(self):
        return f"{self.action} by {self.user} @ {self.created_at}"


class BlockedIP(models.Model):
    """IP addresses blocked from accessing the system."""
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=500, blank=True, default='')
    blocked_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='blocked_ips')
    blocked_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text='Uncheck to unblock without deleting the record')
    failed_attempts = models.PositiveIntegerField(default=0, help_text='Number of blocked requests from this IP')

    class Meta:
        ordering = ['-blocked_at']
        verbose_name = 'Blocked IP'
        verbose_name_plural = 'Blocked IPs'

    def __str__(self):
        status = 'active' if self.is_active else 'inactive'
        return f"{self.ip_address} ({status})"


# Department/office options for visitors (campus destinations)
CAMPUS_DEPARTMENT_CHOICES = (
    ('', '-- Select department/office --'),
    ('registrar', 'Registrar'),
    ('student_affairs', 'Student Affairs and Services'),
    ('cashier', 'Cashier / Accounting'),
    ('library', 'Library'),
    ('guidance', 'Guidance and Counseling'),
    ('clinic', 'Clinic / Health Services'),
    ('admin', "Administrative Office / President's Office"),
    ('academic_affairs', 'Academic Affairs'),
    ('hr', 'Human Resource Office'),
    ('security', 'Security Office'),
    ('canteen', 'Canteen / Cafeteria'),
    ('maintenance', 'Maintenance / Facilities'),
    ('it', 'IT Office'),
    ('other', 'Other'),
)


class VisitorPass(models.Model):
    """
    Reusable visitor QR pass (VIS-001 style) or legacy one-time pass (VISITOR-xxx).
    Reusable: status AVAILABLE | IN_USE | DISABLED; current_visit points to active VisitorVisit.
    Legacy: guest_name/valid_from/valid_until/used_at for one-time use.
    """
    STATUS_AVAILABLE = 'AVAILABLE'
    STATUS_IN_USE = 'IN_USE'
    STATUS_DISABLED = 'DISABLED'
    STATUS_CHOICES = (
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_IN_USE, 'In use'),
        (STATUS_DISABLED, 'Disabled'),
    )
    code = models.CharField(max_length=64, unique=True, db_index=True, help_text='QR payload e.g. VIS-001 or VISITOR-xxx')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True, help_text='Last check-out time (reusable passes)')
    current_visit = models.OneToOneField(
        'VisitorVisit', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pass_current_for',
        help_text='Active visit when status=IN_USE; null after check-out',
    )
    guest_name = models.CharField(max_length=200, blank=True, help_text='Legacy one-time pass: guest name; blank for reusable')
    purpose = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True, help_text='Department/office (legacy or default for reusable)')
    valid_from = models.DateTimeField(null=True, blank=True, help_text='Legacy one-time: valid window start')
    valid_until = models.DateTimeField(null=True, blank=True, help_text='Legacy one-time: valid window end')
    used_at = models.DateTimeField(null=True, blank=True, help_text='Legacy one-time: when consumed')
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='visitor_passes')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Visitor passes'

    def __str__(self):
        if self.guest_name:
            return f"{self.guest_name} ({self.code})"
        return f"{self.code} ({self.get_status_display()})"

    def is_reusable(self):
        """True if this is a reusable slot (VIS-xxx style)."""
        return self.code.startswith('VIS-') and len(self.code) <= 16

    @staticmethod
    def generate_code():
        import secrets
        return 'VISITOR-' + secrets.token_urlsafe(24)

    @staticmethod
    def generate_reusable_code(sequence):
        """Generate VIS-001, VIS-002, ... for printable slot QRs."""
        return f'VIS-{sequence:03d}'


class VisitorVisit(models.Model):
    """
    One visitor check-in/check-out session. Created when a reusable pass (AVAILABLE) is used for check-in;
    closed when the same pass is scanned for check-out (or force checkout by staff).
    """
    STATUS_INSIDE = 'INSIDE'
    STATUS_OUTSIDE = 'OUTSIDE'
    STATUS_CHOICES = (
        (STATUS_INSIDE, 'Inside'),
        (STATUS_OUTSIDE, 'Outside'),
    )
    pass_obj = models.ForeignKey(
        VisitorPass, on_delete=models.CASCADE, related_name='visits',
        help_text='Reusable pass used for this visit',
    )
    full_name = models.CharField(max_length=200)
    purpose = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True, help_text='Department/office visiting')
    photo_in = models.ImageField(upload_to='visitor_visits/%Y/%m/', blank=True, null=True)
    photo_out = models.ImageField(upload_to='visitor_visits/%Y/%m/', blank=True, null=True)
    checked_in_at = models.DateTimeField()
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visitor_visits_checked_in',
    )
    checked_out_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='visitor_visits_checked_out',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INSIDE, db_index=True)
    notes = models.TextField(blank=True)
    id_type = models.CharField(max_length=80, blank=True, help_text='e.g. Government ID, Company ID')
    id_number = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['-checked_in_at']
        verbose_name_plural = 'Visitor visits'

    def __str__(self):
        return f"{self.full_name} @ {self.pass_obj.code} ({self.status})"


class VisitorEntry(models.Model):
    """Manual log when staff allows a visitor to enter campus (name, purpose, who to visit)."""
    visitor_name = models.CharField(max_length=200, help_text='Full name of the visitor')
    purpose = models.CharField(max_length=255, help_text='Purpose of visit (e.g. meeting, delivery)')
    who_to_visit = models.CharField(max_length=255, help_text='Person, office, or department they are visiting')
    recorded_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True,
        related_name='visitor_entries_recorded',
        help_text='Staff user who recorded this entry',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(
        upload_to='visitor_photos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Optional face capture as proof of visitor at entry.',
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Visitor entries'

    def __str__(self):
        return f"{self.visitor_name} – {self.purpose} (visit: {self.who_to_visit}) @ {self.timestamp}"


class StudentBlock(models.Model):
    """Temporary block (or allow) for gate/event access by date range."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='access_blocks')
    reason = models.CharField(max_length=255)
    block_from = models.DateField()
    block_until = models.DateField()
    is_allowlist = models.BooleanField(default=False, help_text='If True, only allow access in this window; else block.')
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='student_blocks_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-block_from']
        verbose_name_plural = 'Student blocks'

    def __str__(self):
        return f"{self.student.student_id} {self.block_from}–{self.block_until}"


class EventWaitlist(models.Model):
    """Waitlist when event is at capacity."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='waitlist_entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='event_waitlist_entries')
    position = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(null=True, blank=True, help_text='When moved from waitlist to registration')

    class Meta:
        unique_together = [['event', 'student']]
        ordering = ['event', 'position']
        verbose_name_plural = 'Event waitlists'

    def __str__(self):
        return f"{self.student.student_id} @ {self.event.name} (#{self.position})"


class RecurringEventTemplate(models.Model):
    """Template for generating recurring events (e.g. weekly)."""
    name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255, blank=True)
    RECURRENCE_CHOICES = (('weekly', 'Weekly'), ('monthly', 'Monthly'))
    recurrence = models.CharField(max_length=20, choices=RECURRENCE_CHOICES, default='weekly')
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0=Monday, 6=Sunday (for weekly)')
    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True, help_text='1-31 (for monthly)')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='recurring_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    last_generated = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Recurring event templates'

    def __str__(self):
        return f"{self.name} ({self.recurrence})"


class SiteTheme(models.Model):
    """Single row: logo, primary color, site name for theming."""
    site_name = models.CharField(max_length=200, default='City College of Bayawan')
    logo = models.ImageField(upload_to='theme/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#28a745', help_text='Hex color e.g. #28a745')
    default_first_signatory_name = models.CharField(max_length=120, blank=True, default='')
    default_first_signatory_title = models.CharField(max_length=120, blank=True, default='')
    default_second_signatory_name = models.CharField(max_length=120, blank=True, default='')
    default_second_signatory_title = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Site theme'

    def __str__(self):
        return self.site_name


class GatePolicy(models.Model):
    """
    Daily time-policy for the gate (single row or per-campus). Drives IN/OUT allow/deny/require-reason.
    """
    name = models.CharField(max_length=80, default='Default', help_text='e.g. Default, Main Gate')
    # Fixed times (use 24h or store as TimeField)
    gate_open_time = models.TimeField(default=datetime.time(7, 0), help_text='Gate opens for entry (e.g. 07:00)')
    lunch_out_start = models.TimeField(default=datetime.time(11, 59, 0), help_text='Lunch OUT allowed from (11:59)')
    lunch_in_start = models.TimeField(default=datetime.time(12, 59, 0), help_text='Lunch IN allowed from (12:59)')
    general_out_until = models.TimeField(default=datetime.time(17, 0), help_text='General OUT allowed until (17:00); after this use last class end')
    # Strict lunch return: deny IN between 11:59–12:59 (student must wait until 12:59 to return)
    strict_lunch_return = models.BooleanField(default=True, help_text='If True, deny IN during 11:59–12:59')
    # Buffer / lunch / gate times: legacy fields kept for admin display; daily gate policy no longer uses class schedules.
    out_buffer_minutes = models.PositiveSmallIntegerField(default=30, help_text='Legacy: was used with class-based OUT rules.')
    permissive_college_mode = models.BooleanField(
        default=True,
        help_text='Legacy toggle. Daily gate now always uses college-style IN/OUT (no class schedule).',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Gate policies'

    def __str__(self):
        return self.name


# --------------- Gate personnel notifications & activity ---------------

class GateNotification(models.Model):
    """
    Notifications for gate personnel: incidents, capacity alerts, shift reminders, suspicious activity.
    Supports broadcast (all on-duty personnel) or targeted (specific user).
    """
    NOTIFICATION_TYPE_CHOICES = (
        ('incident', 'Incident Alert'),
        ('capacity', 'Capacity Alert'),
        ('shift_reminder', 'Shift Reminder'),
        ('suspicious', 'Suspicious Activity'),
        ('system', 'System Message'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField(max_length=1000)
    notify_user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='gate_notifications',
        null=True,
        blank=True,
        verbose_name='Notify user',
        help_text='Specific user to notify (null if broadcast).',
    )
    broadcast = models.BooleanField(default=False, help_text='Send to all on-duty personnel')
    related_incident = models.ForeignKey(GateIncident, on_delete=models.SET_NULL, null=True, blank=True)
    related_event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    related_entry = models.ForeignKey('GateEntry', on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Notification expires after this time')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gate notification'
        verbose_name_plural = 'Gate notifications'
        indexes = [
            models.Index(fields=['notify_user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        target = self.notify_user.username if self.notify_user else 'ALL ON DUTY'
        return f"{self.get_priority_display()}: {self.title} → {target}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.notify_user and not self.broadcast:
            raise ValidationError('Either notify_user must be set or broadcast must be True')
        if self.priority == 'urgent' and self.notification_type not in ('incident', 'suspicious'):
            raise ValidationError('Urgent priority requires notification_type to be incident or suspicious')
        if self.expires_at and self.created_at and self.expires_at <= self.created_at:
            raise ValidationError('Expiration time must be after creation time')


class GateHandoverNote(models.Model):
    """
    Shift handover notes created by gate personnel for communication across shifts.
    Associated with a shift if created during active duty.
    """
    PRIORITY_CHOICES = (
        ('normal', 'Normal'),
        ('important', 'Important'),
        ('urgent', 'Urgent'),
    )
    
    personnel = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='handover_notes_authored',
        verbose_name='Author',
        help_text='User who created this note.',
    )
    shift = models.ForeignKey(
        GateShift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handover_notes',
        help_text='Shift during which this note was created (null if created outside shift)',
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gate handover note'
        verbose_name_plural = 'Gate handover notes'

    def __str__(self):
        return f"{self.personnel.username} - {self.get_priority_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if len(self.content) > 2000:
            raise ValidationError('Note content cannot exceed 2000 characters')


class GateHandoverNoteRead(models.Model):
    """
    Tracks which users have read which notes (for handover acknowledgment).
    """
    note = models.ForeignKey(GateHandoverNote, on_delete=models.CASCADE, related_name='reads')
    personnel = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='handover_note_reads',
        verbose_name='Reader',
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['note', 'personnel']]
        ordering = ['-read_at']
        verbose_name = 'Gate note read'
        verbose_name_plural = 'Gate note reads'

    def __str__(self):
        return f"{self.personnel.username} read note {self.note.id} at {self.read_at.strftime('%Y-%m-%d %H:%M')}"


class GateActivityLog(models.Model):
    """
    Comprehensive audit trail for gate personnel actions.
    Immutable once created - no updates or deletes allowed.
    """
    ACTION_TYPE_CHOICES = (
        ('scan', 'Gate Scan'),
        ('override', 'Override Decision'),
        ('incident', 'Incident Report'),
        ('shift_start', 'Shift Clock In'),
        ('shift_end', 'Shift Clock Out'),
        ('note', 'Note Created'),
        ('visitor_checkin', 'Visitor Check-in'),
        ('visitor_checkout', 'Visitor Check-out'),
        ('early_out', 'Early Out Recorded'),
        ('lookup', 'Student Lookup'),
    )
    
    personnel = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='gate_activity_logs',
        db_index=True,
        verbose_name='Performed by',
        help_text='User who performed this action.',
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, db_index=True)
    description = models.TextField(max_length=500)
    related_entry = models.ForeignKey('GateEntry', on_delete=models.SET_NULL, null=True, blank=True)
    related_incident = models.ForeignKey(GateIncident, on_delete=models.SET_NULL, null=True, blank=True)
    related_shift = models.ForeignKey(GateShift, on_delete=models.SET_NULL, null=True, blank=True)
    related_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    device_id = models.CharField(max_length=128, blank=True, help_text='Scanner device ID')
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text='Client IP address')
    metadata = models.TextField(blank=True, help_text='Additional context (JSON format)')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Gate activity log'
        verbose_name_plural = 'Gate activity logs'
        indexes = [
            models.Index(fields=['personnel', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.personnel.username} - {self.get_action_type_display()} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if len(self.description) > 500:
            raise ValidationError('Description cannot exceed 500 characters')

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError('Gate activity log records are immutable and cannot be updated')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Block direct application-level deletes. Django's CASCADE collector
        # uses QuerySet._raw_delete() and bypasses Model.delete(), so
        # cascaded cleanup (e.g. when a User is deleted) still works.
        raise ValueError('Gate activity log records are immutable and cannot be deleted')


class AdminNotification(models.Model):
    """
    Notifications for admin/staff: student registrations, incidents, capacity alerts, system messages.
    Supports broadcast (all admins/staff) or targeted (specific user).
    """
    NOTIFICATION_TYPE_CHOICES = (
        ('student_registration', 'Student Registration'),
        ('staff_personnel_registration', 'Staff/Faculty/Personnel Registration'),
        ('incident', 'Incident Alert'),
        ('sas_inactive_ready_activation', 'SAS checked — inactive student ready to activate'),
        ('capacity', 'Capacity Alert'),
        ('system', 'System Message'),
        ('personnel_alert', 'Personnel alert'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    title = models.CharField(max_length=200)
    message = models.TextField(max_length=1000)
    target_user = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='admin_notifications', 
        null=True, 
        blank=True,
        help_text='Specific admin/staff to notify (null if broadcast)'
    )
    broadcast = models.BooleanField(default=False, help_text='Send to all admins/staff')
    related_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    related_incident = models.ForeignKey(GateIncident, on_delete=models.SET_NULL, null=True, blank=True)
    related_event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    related_entry = models.ForeignKey(GateEntry, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Notification expires after this time')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin notification'
        verbose_name_plural = 'Admin notifications'
        indexes = [
            models.Index(fields=['target_user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        target = self.target_user.username if self.target_user else 'ALL ADMINS/STAFF'
        return f"{self.get_priority_display()}: {self.title} → {target}"
