from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from captcha.fields import CaptchaField, CaptchaTextInput


User = get_user_model()

# Roles allowed for self-registration (Staff, Faculty, Student Affairs). SAS uses the same pending-approval flow as staff/faculty.
STAFF_PERSONNEL_ROLE_CHOICES = [
    ('staff', 'Staff'),
    ('faculty', 'Faculty'),
    ('student_affairs', 'Student Affairs'),
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


class StaffPersonnelRegistrationForm(forms.Form):
    """Self-registration for Staff, Faculty, and Student Affairs. Account inactive until admin approves.
    After approval, staff/faculty must complete StaffPersonnelProfile; Student Affairs goes straight to the app."""
    role = forms.ChoiceField(
        choices=STAFF_PERSONNEL_ROLE_CHOICES,
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
        label='Middle Initial',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Initial'})
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


class StaffPersonnelCompleteProfileForm(forms.Form):
    """Required profile completion after first login (staff/faculty). Must be filled before full dashboard access."""
    SEX_CHOICES = [
        ('', 'Select sex/gender'),
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
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
    """Change username and email (for staff account settings)."""
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
    """Change password (old, new, confirm) for staff account settings."""
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


# Common choices for staff preferences (language + email only)
PREF_LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('fil', 'Filipino'),
]


class UserPreferencesForm(forms.Form):
    """Preferences for staff/faculty: language and email notifications for announcements only."""
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
    """Edit current user's name, email, profile photo, and (for staff/faculty) profile fields."""
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
    # Optional profile fields (for staff/faculty)
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        label='Middle Initial',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Initial'})
    )
    SEX_CHOICES = [
        ('', 'Select sex/gender'),
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
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


class PasswordResetFormEmailMustExist(PasswordResetForm):
    """
    Same as Django's PasswordResetForm, but rejects unknown emails on the form
    so users get a clear error instead of the generic 'check your email' page.
    Includes a CAPTCHA to limit automated abuse.
    """

    captcha = CaptchaField(
        label='',
        widget=CaptchaTextInput(
            attrs={
                'class': 'form-control captcha-input',
                'placeholder': _('Enter the code shown'),
                'autocomplete': 'off',
            }
        ),
    )

    # Validate CAPTCHA before email so bots cannot probe addresses without solving it.
    field_order = ('captcha', 'email')

    def clean_email(self):
        email = self.cleaned_data['email']
        if not any(self.get_users(email)):
            raise ValidationError(
                _('No account is registered with this email address. Please check and try again.'),
                code='unknown_email',
            )
        return email


class PasswordResetFormEmailOrUsername(forms.Form):
    """
    Password reset request that accepts either an email address or a username
    in the single 'email' field (kept for compatibility with Django's template).
    """
    email = forms.CharField(
        label='Email or username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email or username',
            'autocomplete': 'email',
        }),
        max_length=254,
    )

    def get_users(self, identifier: str):
        """
        Yield active users matching either email (case-insensitive) or username (case-insensitive).
        """
        if not identifier:
            return []
        # First try by email
        users_qs = User._default_manager.filter(email__iexact=identifier, is_active=True)
        if not users_qs.exists():
            # Fallback: treat identifier as username
            users_qs = User._default_manager.filter(username__iexact=identifier, is_active=True)
        return list(users_qs)

    def get_user_emails(self, users):
        emails = []
        for u in users:
            email = (u.email or '').strip()
            if email:
                emails.append(email)
        return emails

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=None,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Mirror django.contrib.auth.forms.PasswordResetForm.save behavior but resolve users
        by either email or username, and send to their registered email addresses.
        """
        from django.contrib.auth.tokens import default_token_generator
        from django.template.loader import render_to_string
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.core.mail import EmailMultiAlternatives

        identifier = (self.cleaned_data.get('email') or '').strip()
        users = self.get_users(identifier)
        if not users:
            # For security, behave as if we processed it; mimic Django's default (do nothing)
            return

        token_generator = token_generator or default_token_generator
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            context = {
                'email': user.email,
                'domain': domain_override or (request.get_host() if request else ''),
                'site_name': (extra_email_context or {}).get('site_name'),
                'uid': uid,
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            subject = render_to_string(subject_template_name, context)
            subject = ''.join(subject.splitlines())
            body = render_to_string(email_template_name, context)
            email_message = EmailMultiAlternatives(subject, body, from_email, [user.email])
            if html_email_template_name is not None:
                html_email = render_to_string(html_email_template_name, context)
                email_message.attach_alternative(html_email, 'text/html')
            email_message.send()


def _normalize_phone(value):
    """Return digits only from phone string."""
    import re
    return re.sub(r'\D', '', str(value or ''))


class PhoneResetRequestForm(forms.Form):
    """Request a verification code sent to the user's registered phone (StaffPersonnelProfile.contact_number)."""
    phone = forms.CharField(
        label='Phone number',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 09XXXXXXXXX',
            'autocomplete': 'tel',
            'inputmode': 'numeric',
        }),
    )

    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        normalized = _normalize_phone(raw)
        if len(normalized) < 10:
            raise forms.ValidationError('Enter a valid phone number (at least 10 digits).')
        return normalized


class VerifyCodeForm(forms.Form):
    """Enter the 6-digit verification code sent via SMS."""
    code = forms.CharField(
        label='Verification code',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'maxlength': '6',
            'pattern': '[0-9]*',
        }),
    )

    def clean_code(self):
        raw = (self.cleaned_data.get('code') or '').strip()
        if not raw.isdigit() or len(raw) != 6:
            raise forms.ValidationError('Enter the 6-digit code from your phone.')
        return raw


class NewPasswordForm(forms.Form):
    """Set new password after phone verification."""
    new_password = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password',
            'autocomplete': 'new-password',
        }),
    )
    new_password_confirm = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        }),
    )

    def clean_new_password(self):
        p = self.cleaned_data.get('new_password')
        if p and len(p) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return p

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('new_password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password_confirm', 'Passwords do not match.')
        return cleaned