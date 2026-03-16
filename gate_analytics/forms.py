from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()

# Roles allowed for self-registration (Staff, Faculty, Guard). Admin/Supervisor stay admin-created.
STAFF_GUARD_ROLE_CHOICES = [
    ('staff', 'Staff'),
    ('faculty', 'Faculty'),
    ('guard', 'Guard'),
]


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'type': 'text',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'type': 'password',
        'placeholder': 'Password'
    }))


class StaffGuardRegistrationForm(forms.Form):
    """Self-registration for Staff, Faculty, and Guard. Account details only; account inactive until admin approves.
    After approval, user must complete profile (sex, birthdate, address, etc.) before full dashboard access."""
    role = forms.ChoiceField(
        choices=STAFF_GUARD_ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control reg-role-select', 'aria-label': 'Role'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username (for login)',
            'autocomplete': 'username',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address', 'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle name'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'new-password',
        })
    )
    password_confirm = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
        })
    )

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError('Username is required.')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError('Email is required.')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned


REQUIRED_MSG = 'This field is required.'


class StaffGuardCompleteProfileForm(forms.Form):
    """Required profile completion after first login (staff/faculty/guard). Must be filled before full dashboard access."""
    SEX_CHOICES = [
        ('', 'Select sex/gender'),
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('PREFER_NOT', 'Prefer not to say'),
    ]
    sex = forms.ChoiceField(
        required=True,
        choices=SEX_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={'required': REQUIRED_MSG, 'invalid_choice': 'Please select a valid option.'},
    )
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        error_messages={'required': REQUIRED_MSG, 'invalid': 'Enter a valid date.'},
    )
    address = forms.CharField(
        max_length=500,
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 2}),
        error_messages={'required': REQUIRED_MSG},
    )
    contact_number = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number', 'maxlength': '20'}),
        error_messages={'required': REQUIRED_MSG},
    )
    employee_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee / ID number'}),
        error_messages={'required': REQUIRED_MSG},
    )
    department = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department / Office'}),
        error_messages={'required': REQUIRED_MSG},
    )
    position = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Position / Title'}),
        error_messages={'required': REQUIRED_MSG},
    )
    photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*',
        }),
        label='Profile photo',
        help_text='Optional. Shown in the sidebar.',
    )

    def clean_contact_number(self):
        data = (self.cleaned_data.get('contact_number') or '').strip().replace(' ', '').replace('-', '')
        if not data:
            raise ValidationError(REQUIRED_MSG)
        digits = ''.join(c for c in data if c.isdigit())
        if len(digits) > 20:
            return digits[:20]
        return digits or data

    def clean_birthdate(self):
        from django.utils import timezone
        data = self.cleaned_data.get('birthdate')
        if not data:
            raise ValidationError(REQUIRED_MSG)
        if data > timezone.now().date():
            raise ValidationError('Birthdate cannot be in the future.')
        return data


class AccountDetailsForm(forms.Form):
    """Change username and email (for staff/guard account settings)."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'autocomplete': 'username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address', 'autocomplete': 'email'})
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError('Username is required.')
        if self.user and User.objects.filter(username__iexact=username).exclude(pk=self.user.pk).exists():
            raise ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError('Email is required.')
        if self.user and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError('This email is already registered.')
        return email


class PasswordChangeForm(forms.Form):
    """Change password (old, new, confirm) for staff/guard account settings."""
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Old password',
            'autocomplete': 'current-password',
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'autocomplete': 'new-password',
        }),
        help_text='Use at least 8 characters, mix upper and lower case letters, numbers, and symbols.',
    )
    new_password_confirm = forms.CharField(
        label='New password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data.get('old_password')
        if self.user and old and not self.user.check_password(old):
            raise ValidationError('Your old password was entered incorrectly.')
        return old

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        confirm = cleaned.get('new_password_confirm')
        if new and confirm and new != confirm:
            self.add_error('new_password_confirm', 'The two password fields did not match.')
        if new and len(new) < 8:
            self.add_error('new_password', 'Password must be at least 8 characters.')
        return cleaned


# Common choices for staff/guard preferences (language + email only)
PREF_LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('fil', 'Filipino'),
]


class UserPreferencesForm(forms.Form):
    """Preferences for staff/guard/faculty: language and email notifications for announcements only."""
    preferred_language = forms.ChoiceField(
        choices=PREF_LANGUAGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Pref language',
    )
    email_notifications_announcements = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Email notifications for announcements',
    )


class UserProfileEditForm(forms.Form):
    """Edit current user's name, email, profile photo, and (for staff/faculty/guard) profile fields."""
    avatar = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*',
        }),
        help_text='Upload a profile photo (optional). Shown in the sidebar.',
    )
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email', 'autocomplete': 'email'})
    )
    # Optional profile fields (for staff/faculty/guard)
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle name'})
    )
    SEX_CHOICES = [
        ('', 'Select sex/gender'),
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('PREFER_NOT', 'Prefer not to say'),
    ]
    sex = forms.ChoiceField(
        required=False,
        choices=SEX_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    birthdate = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    address = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 2})
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'})
    )
    employee_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee / ID number'})
    )
    department = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department / Office'})
    )
    position = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Position / Title'})
    )