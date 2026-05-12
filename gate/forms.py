from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy
from betterforms.multiform import MultiModelForm

from .models import Event, EventImage, EventAgenda, Student, EventCategory, JobCategory, SiteTheme
from .event_category_utils import get_or_create_custom_event_category


def validate_student_birthdate_not_in_current_year(value):
    if value is None:
        return
    today = timezone.now().date()
    if value.year >= today.year:
        month_year = value.strftime('%B %Y')
        raise ValidationError(
            format_lazy(
                _(
                    'You cannot choose this month and year ({month_year}): birthdates in the current calendar year are not allowed.'
                ),
                month_year=month_year,
            )
        )


class EventStatusForm(forms.ModelForm):
    """Form for updating event status only. Explicitly uses full STATUS_CHOICES so draft can be set to Active."""
    class Meta:
        model = Event
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = Event.STATUS_CHOICES
        self.fields['status'].help_text = 'Set to Active to make this event available for gate tracking.'

# Face photo: capstone-ready validation (safe for gate verification)
PHOTO_MAX_MB = 5
PHOTO_MIN_WIDTH = 400
PHOTO_MIN_HEIGHT = 400


def validate_student_photo(file):
    """Validate face photo: type, size, and minimum dimensions (server-side, cannot be bypassed)."""
    if file.size > PHOTO_MAX_MB * 1024 * 1024:
        raise ValidationError(f'Photo must be under {PHOTO_MAX_MB}MB.')
    try:
        from PIL import Image
        img = Image.open(file)
        img.verify()
    except ImportError:
        pass
    except Exception:
        raise ValidationError('Invalid or corrupted image file.')
    file.seek(0)
    try:
        img = Image.open(file)
        w, h = img.size
        if w < PHOTO_MIN_WIDTH or h < PHOTO_MIN_HEIGHT:
            raise ValidationError(
                f'Photo too small. Use at least {PHOTO_MIN_WIDTH}x{PHOTO_MIN_HEIGHT} pixels for clear gate verification.'
            )
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError('Could not read image dimensions.')


class EventForm(forms.ModelForm):
    use_custom_category = forms.CharField(
        required=False,
        max_length=1,
        widget=forms.HiddenInput(),
        initial='',
    )
    custom_category_name = forms.CharField(
        required=False,
        max_length=255,
        label=_('Category name'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Type a new category name'),
                'autocomplete': 'off',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self._creating_user = kwargs.pop('creating_user', None) or kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if 'category' in self.fields:
            category_qs = EventCategory.objects.filter(status='active').order_by('priority', 'name')
            if not category_qs.exists():
                category_qs = EventCategory.objects.all().order_by('priority', 'name')
            self.fields['category'].queryset = category_qs
            self.fields['category'].widget.attrs.update({'class': 'form-control'})
            self.fields['category'].required = False
        if 'job_category' in self.fields:
            self.fields['job_category'].queryset = JobCategory.objects.all().order_by('name')
            self.fields['job_category'].widget.attrs.update({'class': 'form-control'})
        for k in (
            'name', 'venue',
            'status',
            'audience_scope', 'audience_course', 'audience_year_level', 'audience_section',
        ):
            if k in self.fields:
                self.fields[k].widget.attrs.setdefault('class', 'form-control')
        if 'event_location' in self.fields:
            self.fields['event_location'].widget = forms.RadioSelect()
            self.fields['event_location'].label = 'Where is it held?'
            self.fields['event_location'].help_text = 'On campus, or off campus (e.g. field trip). Same scanner either way.'
            self.fields['event_location'].choices = [
                ('on_campus', 'On campus'),
                ('field_trip', 'Off campus / field trip'),
            ]
        if 'venue' in self.fields:
            self.fields['venue'].label = 'Place name'
            self.fields['venue'].help_text = 'Room, building, or address (optional).'
            self.fields['venue'].widget.attrs.setdefault(
                'placeholder',
                'e.g. Main Gym, AVR Room 2, City Museum…',
            )
        if 'audience_scope' in self.fields:
            self.fields['audience_scope'].widget.attrs.setdefault('class', 'form-control')
            self.fields['audience_scope'].help_text = 'Choose who is allowed/expected to attend this event.'
        if 'audience_course' in self.fields:
            self.fields['audience_course'].required = False
            self.fields['audience_course'].widget = forms.Select(
                choices=[('', 'Select program')] + list(Student.COURSE_CHOICES),
                attrs={'class': 'form-control'}
            )
            self.fields['audience_course'].help_text = 'Used when scope includes program.'
        if 'audience_year_level' in self.fields:
            self.fields['audience_year_level'].required = False
            self.fields['audience_year_level'].widget = forms.Select(
                choices=[('', 'Select year level')] + list(Student.YEAR_LEVEL_CHOICES),
                attrs={'class': 'form-control'}
            )
            self.fields['audience_year_level'].help_text = 'Used when scope includes year level.'
        if 'audience_section' in self.fields:
            self.fields['audience_section'].required = False
            self.fields['audience_section'].widget.attrs.setdefault('class', 'form-control')
            self.fields['audience_section'].widget.attrs.setdefault('placeholder', 'e.g. A or 1A')
            self.fields['audience_section'].help_text = 'Used when scope is program + section.'
        if 'uid' in self.fields:
            self.fields['uid'].required = False
        if 'description' in self.fields:
            self.fields['description'].required = False
            self.fields['description'].help_text = 'Optional. You can add details later.'
        if 'venue' in self.fields:
            self.fields['venue'].required = False

        # Not shown on create/edit UI; still submitted (defaults: auto uid, OPEN mode, optional job/points)
        for _adv in ('uid', 'job_category', 'attendance_mode', 'points'):
            if _adv in self.fields:
                self.fields[_adv].widget = forms.HiddenInput()
                self.fields[_adv].help_text = ''

    def clean(self):
        cleaned_data = super().clean()
        scope = (cleaned_data.get('audience_scope') or 'all').strip().lower()
        course = (cleaned_data.get('audience_course') or '').strip().upper()
        year = (cleaned_data.get('audience_year_level') or '').strip()
        section = (cleaned_data.get('audience_section') or '').strip()

        if scope in ('course', 'course_year', 'course_section', 'course_section_year') and not course:
            self.add_error('audience_course', 'Select a program for this audience scope.')
        if scope in ('year_level', 'course_year', 'course_section_year') and not year:
            self.add_error('audience_year_level', 'Select a year level for this audience scope.')
        if scope in ('course_section', 'course_section_year') and not section:
            self.add_error('audience_section', 'Enter the section for this audience scope.')

        # Keep data clean: clear fields not needed by selected scope.
        if scope not in ('course', 'course_year', 'course_section', 'course_section_year'):
            cleaned_data['audience_course'] = ''
        else:
            cleaned_data['audience_course'] = course
        if scope not in ('year_level', 'course_year', 'course_section_year'):
            cleaned_data['audience_year_level'] = ''
        else:
            cleaned_data['audience_year_level'] = year
        if scope not in ('course_section', 'course_section_year'):
            cleaned_data['audience_section'] = ''
        else:
            cleaned_data['audience_section'] = section

        use_custom = (cleaned_data.get('use_custom_category') or '').strip() == '1'
        custom_name = (cleaned_data.get('custom_category_name') or '').strip()
        user = getattr(self, '_creating_user', None)

        if use_custom:
            if not custom_name:
                self.add_error('custom_category_name', _('Enter a name for your custom category.'))
            elif user is None:
                self.add_error(
                    None,
                    _('Unable to create a custom category on this form. Please refresh and try again.'),
                )
            else:
                try:
                    cleaned_data['category'] = get_or_create_custom_event_category(custom_name, user)
                except ValueError as exc:
                    self.add_error('custom_category_name', str(exc))
        else:
            cleaned_data['custom_category_name'] = ''
            cleaned_data['use_custom_category'] = ''
            if not cleaned_data.get('category'):
                self.add_error('category', _('Please select a category.'))

        return cleaned_data


    class Meta:
        model = Event
        fields = [
            'category', 'name', 'uid', 'description', 'job_category',
            'venue', 'start_date', 'end_date', 'points',
            'attendance_mode', 'event_location',
            'audience_scope', 'audience_course', 'audience_year_level', 'audience_section',
            'status',
            'use_custom_category', 'custom_category_name',
        ]
        widgets = {
            'start_date': forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class EventImageForm(forms.ModelForm):

    class Meta:
        model = EventImage
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'image' in self.fields:
            self.fields['image'].required = False
            self.fields['image'].help_text = 'Optional. You can add one later when editing the event.'



class EventAgendaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].widget.attrs.setdefault('class', 'form-control form-control-sm')

    class Meta:
        model = EventAgenda
        fields = ['session_name', 'speaker_name', 'start_time', 'end_time', 'venue_name']
        labels = {
            'venue_name': 'Session room or area',
        }
        widgets = {
            'start_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
        }


# Inline formset for multiple agenda rows per event (edit page)
EventAgendaFormSet = inlineformset_factory(
    Event,
    EventAgenda,
    form=EventAgendaForm,
    extra=2,
    max_num=20,
    can_delete=True,
)


class EventCreateMultiForm(MultiModelForm):
    form_classes = {
        'event': EventForm,
        'event_image': EventImageForm,
        'event_agenda': EventAgendaForm,
    }

    def __init__(self, *args, **kwargs):
        creating_user = kwargs.pop('creating_user', None)
        super().__init__(*args, **kwargs)
        if creating_user is not None and getattr(self, 'forms', None) and 'event' in self.forms:
            self.forms['event']._creating_user = creating_user


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'student_id', 'first_name', 'middle_name', 'last_name', 'email',
            'birthdate', 'sex', 'contact_number',
            'address',
            'course', 'year_level', 'section',
            'guardians_parents', 'guardian_contact',
            'photo', 'signature',
            'account_status',
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID embedded in QR code (max 8 digits)', 'maxlength': '8', 'pattern': '[0-9]*', 'inputmode': 'numeric'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Initial'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@school.edu'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'birthdate': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'guardians_parents': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guardian(s) or parent(s) name(s)'}),
            'guardian_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number', 'maxlength': '11', 'pattern': '[0-9]*', 'inputmode': 'numeric'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'year_level': forms.Select(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A, 1A'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your contact number', 'maxlength': '11', 'pattern': '[0-9]*', 'inputmode': 'numeric'}),
            'account_status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sex'].required = True
        self.fields['sex'].choices = list(Student.SEX_CHOICES)
        if 'birthdate' in self.fields:
            self.fields['birthdate'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_birthdate(self):
        data = self.cleaned_data.get('birthdate')
        if not data:
            return data
        if self.instance and self.instance.pk and data == self.instance.birthdate:
            return data
        validate_student_birthdate_not_in_current_year(data)
        return data

    def clean_sex(self):
        v = (self.cleaned_data.get('sex') or '').strip()
        if not v:
            raise ValidationError(_('Sex / gender is required.'))
        return v

    def clean_student_id(self):
        data = (self.cleaned_data.get('student_id') or '').strip()
        if not data:
            return data
        # When editing, allow keeping existing ID even if it doesn't match new rules
        if self.instance and self.instance.pk and data == self.instance.student_id:
            return data
        if len(data) > 8:
            raise ValidationError('Student ID must be at most 8 digits.')
        if not data.isdigit():
            raise ValidationError('Student ID must contain only digits (0–9).')
        return data

    def _clean_phone_11(self, value, field_label):
        data = (value or '').strip().replace(' ', '').replace('-', '')
        if not data:
            return ''
        digits = ''.join(c for c in data if c.isdigit())
        if len(digits) > 11:
            raise ValidationError(f'{field_label} must be at most 11 digits.')
        return digits

    def clean_contact_number(self):
        return self._clean_phone_11(
            self.cleaned_data.get('contact_number'),
            'Your contact number',
        )

    def clean_guardian_contact(self):
        return self._clean_phone_11(
            self.cleaned_data.get('guardian_contact'),
            'Contact number',
        )


class StudentModalForm(StudentForm):
    """Quick-add fields for the student list modal. Defaults to Active account_status."""

    class Meta(StudentForm.Meta):
        fields = [
            'student_id', 'first_name', 'middle_name', 'last_name', 'email',
            'birthdate', 'sex', 'contact_number',
            'address',
            'course', 'year_level', 'section',
            'guardians_parents', 'guardian_contact',
            'photo', 'signature',
        ]


class StudentStudentAffairsForm(StudentForm):
    """Student Affairs office: uses the same student form fields, including account status."""


class StudentAdminForm(forms.ModelForm):
    """Django admin: sex/gender required (same policy as Gate student create/edit)."""

    class Meta:
        model = Student
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sex'].required = True
        self.fields['sex'].choices = list(Student.SEX_CHOICES)
        if 'birthdate' in self.fields:
            self.fields['birthdate'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_birthdate(self):
        data = self.cleaned_data.get('birthdate')
        if not data:
            return data
        if self.instance and self.instance.pk and data == self.instance.birthdate:
            return data
        validate_student_birthdate_not_in_current_year(data)
        return data

    def clean_sex(self):
        v = (self.cleaned_data.get('sex') or '').strip()
        if not v:
            raise ValidationError(_('Sex / gender is required.'))
        return v


class StudentRegistrationForm(forms.Form):
    """Legacy fields for student intake (no longer used on the public /register/ page)."""
    student_id = forms.CharField(
        max_length=8,
        required=False,
        label='ID number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID number', 'maxlength': '8', 'pattern': '[0-9]*', 'inputmode': 'numeric'})
    )
    first_name = forms.CharField(
        max_length=100,
        label='First name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        label='Middle Initial',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Initial'})
    )
    last_name = forms.CharField(
        max_length=100,
        label='Last name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    address = forms.CharField(
        max_length=500,
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 2})
    )
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    sex = forms.ChoiceField(
        required=True,
        label='Sex / Gender',
        choices=[('', 'Select sex/gender')] + list(Student.SEX_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    guardians_parents = forms.CharField(
        max_length=255,
        required=True,
        label='Guardians / Parents',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guardian(s) or parent(s) name(s)'})
    )
    email = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    course = forms.ChoiceField(
        required=True,
        label='Program',
        choices=[('', 'Select program')] + list(Student.COURSE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    year_level = forms.ChoiceField(
        required=True,
        label='Year level',
        choices=[('', 'Select year level')] + list(Student.YEAR_LEVEL_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    section = forms.CharField(
        required=True,
        max_length=20,
        label='Section',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Section (e.g. A / 1A / BSIT-1A)'})
    )
    contact_number = forms.CharField(
        required=True,
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your contact number',
            'maxlength': '11',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
        })
    )
    guardian_contact = forms.CharField(
        required=True,
        max_length=11,
        label='Contact number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contact number',
            'maxlength': '11',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
        })
    )
    photo = forms.ImageField(
        required=True,
        label='Face photo',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'capture': 'user',
        }),
        validators=[validate_student_photo],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birthdate'].widget.attrs['max'] = timezone.now().date().isoformat()

    def _name_ok(self, value):
        return (value or '').replace(' ', '').replace('-', '').replace("'", '').replace('.', '').isalpha()

    def clean_first_name(self):
        data = (self.cleaned_data.get('first_name') or '').strip()
        if not data:
            raise ValidationError('First name is required.')
        if len(data) < 2:
            raise ValidationError('First name must be at least 2 characters.')
        if not self._name_ok(data):
            raise ValidationError('First name should contain only letters.')
        return data

    def clean_last_name(self):
        data = (self.cleaned_data.get('last_name') or '').strip()
        if not data:
            raise ValidationError('Last name is required.')
        if len(data) < 2:
            raise ValidationError('Last name must be at least 2 characters.')
        if not self._name_ok(data):
            raise ValidationError('Last name should contain only letters.')
        return data

    def clean_middle_name(self):
        data = (self.cleaned_data.get('middle_name') or '').strip()
        if data and not self._name_ok(data):
            raise ValidationError('Middle Initial should contain only letters.')
        return data

    def clean_birthdate(self):
        data = self.cleaned_data.get('birthdate')
        if data:
            if data > timezone.now().date():
                raise ValidationError('Birthdate cannot be in the future.')
            validate_student_birthdate_not_in_current_year(data)
        return data

    def clean_email(self):
        data = (self.cleaned_data.get('email') or '').strip().lower()
        if not data:
            raise ValidationError('Email address is required.')
        if Student.objects.filter(email__iexact=data).exists():
            raise ValidationError('This email address is already registered.')
        return data

    def clean_student_id(self):
        data = (self.cleaned_data.get('student_id') or '').strip()
        if not data:
            return None
        if len(data) > 8:
            raise ValidationError('Student ID must be at most 8 digits.')
        if not data.isdigit():
            raise ValidationError('Student ID must contain only digits (0–9).')
        return data

    def _clean_phone(self, value, field_name):
        data = (value or '').strip().replace(' ', '').replace('-', '')
        if not data:
            return ''
        digits = ''.join(c for c in data if c.isdigit())
        if len(digits) > 11:
            raise ValidationError(f'{field_name} must be at most 11 digits.')
        return digits

    def clean_contact_number(self):
        return self._clean_phone(
            self.cleaned_data.get('contact_number'),
            'Your contact number',
        )

    def clean_guardian_contact(self):
        return self._clean_phone(
            self.cleaned_data.get('guardian_contact'),
            'Contact number',
        )


class StaffPersonnelCreateForm(forms.Form):
    """Admin: create staff, faculty, or SAS (Student Affairs) user (+ profile for staff/faculty only)."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        label='Middle Initial',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Initial'}),
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password_confirm = forms.CharField(label='Confirm password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=(
            ('staff', 'Staff'),
            ('faculty', 'Faculty'),
            ('student_affairs', 'SAS'),
        ),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    department = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    position = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contact_number = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    is_active = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_username(self):
        from django.contrib.auth import get_user_model
        u = (self.cleaned_data.get('username') or '').strip()
        if not u:
            raise ValidationError('Username is required.')
        if get_user_model().objects.filter(username__iexact=u).exists():
            raise ValidationError('This username is already taken.')
        return u

    def clean(self):
        data = super().clean()
        p1 = data.get('password') or ''
        p2 = data.get('password_confirm') or ''
        if p1 != p2:
            raise ValidationError('Passwords do not match.')
        if len(p1) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return data


SIGNATURE_IMAGE_MAX_MB = 3


class SiteThemeEidSignatoryForm(forms.ModelForm):
    """In-app settings for printed e-ID back-of-card signatories (names + signature images)."""

    class Meta:
        model = SiteTheme
        fields = [
            'default_first_signatory_name',
            'default_first_signatory_title',
            'default_second_signatory_name',
            'default_second_signatory_title',
            'first_signatory_signature',
            'second_signatory_signature',
        ]
        widgets = {
            'default_first_signatory_name': forms.TextInput(attrs={'class': 'form-control'}),
            'default_first_signatory_title': forms.TextInput(attrs={'class': 'form-control'}),
            'default_second_signatory_name': forms.TextInput(attrs={'class': 'form-control'}),
            'default_second_signatory_title': forms.TextInput(attrs={'class': 'form-control'}),
            'first_signatory_signature': forms.ClearableFileInput(attrs={'class': 'form-control border-0 pl-0'}),
            'second_signatory_signature': forms.ClearableFileInput(attrs={'class': 'form-control border-0 pl-0'}),
        }

    def _validate_sig_file(self, f, field_label):
        if not f:
            return f
        if f.size > SIGNATURE_IMAGE_MAX_MB * 1024 * 1024:
            raise ValidationError(
                _('%(label)s must be under %(mb)s MB.'),
                params={'label': field_label, 'mb': f'{SIGNATURE_IMAGE_MAX_MB:.2g}'},
            )
        try:
            from PIL import Image
            img = Image.open(f)
            img.verify()
        except ImportError:
            return f
        except Exception:
            raise ValidationError(_('%(label)s is not a valid image file.'), params={'label': field_label})
        f.seek(0)
        return f

    def clean_first_signatory_signature(self):
        f = self.cleaned_data.get('first_signatory_signature')
        return self._validate_sig_file(f, _('First signatory signature'))

    def clean_second_signatory_signature(self):
        f = self.cleaned_data.get('second_signatory_signature')
        return self._validate_sig_file(f, _('Second signatory signature'))


class SiteThemeReportSignatoryForm(forms.ModelForm):
    """Single signatory for Reports → Exports (CSV/Excel/PDF/print only — not e-ID cards)."""

    class Meta:
        model = SiteTheme
        fields = [
            'report_first_signatory_name',
            'report_first_signatory_title',
            'report_first_signatory_signature',
        ]
        widgets = {
            'report_first_signatory_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'report_first_signatory_title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'report_first_signatory_signature': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean_report_first_signatory_signature(self):
        f = self.cleaned_data.get('report_first_signatory_signature')
        return SiteThemeEidSignatoryForm()._validate_sig_file(f, _('Report signatory signature'))

