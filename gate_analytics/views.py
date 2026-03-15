import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.core.cache import cache
from django.conf import settings as django_settings

from django.contrib.auth.models import User, Group
from gate.models import EventCategory, Event, Student, GateEntry, GateIncident, AuditLog, GuardShift, StaffGuardProfile
from gate.gate_views import _granted_visits_count_for_date, _local_day_bounds
from .forms import LoginForm, StaffGuardRegistrationForm, StaffGuardCompleteProfileForm, UserProfileEditForm, AccountDetailsForm, PasswordChangeForm, UserPreferencesForm
from .roles import get_user_role, role_required


@require_GET
def privacy_policy(request):
    """Public privacy & data policy page (no login required)."""
    return render(request, 'legal/privacy_policy.html', {
        'site_name': 'City College of Bayawan',
    })


@require_GET
def terms_and_conditions(request):
    """Public terms and conditions page (no login required)."""
    return render(request, 'legal/terms_and_conditions.html', {
        'site_name': 'City College of Bayawan',
    })


@require_GET
def health_check(request):
    """Lightweight health/readiness check: 200 if app and DB are up. For monitoring/load balancers."""
    from django.http import HttpResponse
    from django.db import connection
    try:
        connection.ensure_connection()
        return HttpResponse('ok', content_type='text/plain', status=200)
    except Exception:
        return HttpResponse('unavailable', content_type='text/plain', status=503)


def custom_page_not_found_view(request, exception):
    """Branded 404 page."""
    return render(request, 'errors/404.html', {'site_name': 'City College of Bayawan'}, status=404)


def custom_server_error_view(request):
    """Branded 500 page."""
    return render(request, 'errors/500.html', {'site_name': 'City College of Bayawan'}, status=500)


@login_required(login_url='login')
@role_required('admin')
def user_list(request):
    """List app users with roles (admin only)."""
    users_list = []
    for u in User.objects.all().order_by('username'):
        users_list.append({
            'user': u,
            'role': get_user_role(u) or '—',
        })
    return render(request, 'users/user_list.html', {
        'site_name': 'City College of Bayawan',
        'users_list': users_list,
    })

@login_required(login_url='login')
@role_required('admin', 'faculty', 'staff', 'guard', 'supervisor')
def dashboard(request):
    if get_user_role(request.user) == 'guard':
        return redirect('guard-dashboard')
    today = timezone.localdate()
    cache_seconds = getattr(django_settings, 'CACHE_DASHBOARD_SECONDS', 120)
    cache_key = f'dashboard_counts_{today.isoformat()}'
    counts = cache.get(cache_key)
    if counts is None:
        day_start, day_end = _local_day_bounds(today)
        granted_today = _granted_visits_count_for_date(today, daily_gate_only=True)
        denied_entries_count = GateEntry.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end, granted=False).count()
        incidents_today = GateIncident.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
        denied_today = max(denied_entries_count, incidents_today)
        total_students = Student.objects.filter(is_active=True).count()
        counts = {
            'granted_today': granted_today,
            'denied_today': denied_today,
            'incidents_today': incidents_today,
            'total_students': total_students,
        }
        cache.set(cache_key, counts, cache_seconds)
    else:
        granted_today = counts['granted_today']
        denied_today = counts['denied_today']
        incidents_today = counts['incidents_today']
        total_students = counts['total_students']
    user = User.objects.count()
    event_ctg = EventCategory.objects.count()
    event = Event.objects.count()
    complete_event = Event.objects.filter(status='completed').count()
    events = Event.objects.all()
    # Guards currently on duty (clocked in via My shift / Clock in on guard dashboard)
    guards_on_duty_list = list(GuardShift.objects.filter(shift_end__isnull=True).select_related('guard').order_by('-shift_start'))
    context = {
        'user': user,
        'event_ctg': event_ctg,
        'event': event,
        'complete_event': complete_event,
        'events': events,
        'today': today,
        'site_name': 'City College of Bayawan',
        'granted_today': granted_today,
        'denied_today': denied_today,
        'incidents_today': incidents_today,
        'total_students': total_students,
        'guards_on_duty_list': guards_on_duty_list,
        'guards_on_duty_count': len(guards_on_duty_list),
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required(login_url='login')
@role_required('admin', 'faculty', 'staff', 'supervisor')
def dashboard_stats_api(request):
    """
    API endpoint for real-time dashboard stats updates.
    Returns JSON with current counts.
    """
    from django.http import JsonResponse
    
    today = timezone.localdate()
    day_start, day_end = _local_day_bounds(today)
    
    # Get fresh counts (no cache for real-time)
    # Count ALL granted entries (students + visitors + events)
    granted_today = GateEntry.objects.filter(
        timestamp__gte=day_start, 
        timestamp__lt=day_end, 
        granted=True
    ).count()
    
    denied_entries_count = GateEntry.objects.filter(
        timestamp__gte=day_start, 
        timestamp__lt=day_end, 
        granted=False
    ).count()
    incidents_today = GateIncident.objects.filter(
        timestamp__gte=day_start, 
        timestamp__lt=day_end
    ).count()
    denied_today = max(denied_entries_count, incidents_today)
    total_students = Student.objects.filter(is_active=True).count()
    
    # Guards on duty count
    guards_on_duty_count = GuardShift.objects.filter(shift_end__isnull=True).count()
    
    return JsonResponse({
        'success': True,
        'granted_today': granted_today,
        'denied_today': denied_today,
        'incidents_today': incidents_today,
        'total_students': total_students,
        'guards_on_duty_count': guards_on_duty_count,
    })


def login_page(request):
    from django.contrib import messages
    from gate.forms import StudentRegistrationForm
    forms = LoginForm()
    reg_form = StudentRegistrationForm()
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        forms = LoginForm(request.POST)
        if forms.is_valid():
            username = forms.cleaned_data['username']
            password = forms.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    forms.add_error(None, 'Your account is pending approval. An administrator must approve it before you can log in.')
                else:
                    role = get_user_role(user)
                    if role is None:
                        messages.error(request, 'Your account has no role (Admin, Faculty, Staff, or Guard). Contact the administrator.')
                        return render(request, 'auth/login.html', {
                            'form': forms, 'next': next_url, 'reg_form': reg_form,
                            'staff_guard_form': StaffGuardRegistrationForm(),
                            'site_name': 'City College of Bayawan'
                        })
                    login(request, user)
                    # Record login for admin "View logs"
                    try:
                        ip = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip() or request.META.get('REMOTE_ADDR') or ''
                        AuditLog.objects.create(
                            user=user,
                            action='login',
                            description='User logged in',
                            ip_address=ip[:45] if ip else None,
                        )
                    except Exception:
                        pass
                    # Staff/Guard/Faculty must complete profile before full access
                    if role in ('staff', 'faculty', 'guard'):
                        profile, _ = StaffGuardProfile.objects.get_or_create(
                            user=user, defaults={'profile_complete': False}
                        )
                        if not getattr(profile, 'profile_complete', False):
                            return redirect('staff-guard-complete-profile')
                    redirect_to = request.POST.get('next') or request.GET.get('next')
                    if role == 'guard':
                        # Guards always go to guard dashboard after login (never gate-scan)
                        redirect_to = 'guard-dashboard'
                    elif not redirect_to:
                        redirect_to = 'dashboard'
                    return redirect(redirect_to)
            else:
                # Django's authenticate() returns None for inactive users; check if credentials are correct but account is pending approval
                try:
                    from django.contrib.auth import get_user_model
                    UserModel = get_user_model()
                    pending_user = UserModel.objects.get(username__iexact=username)
                    if not pending_user.is_active and pending_user.check_password(password):
                        forms.add_error(None, 'Your account is pending approval. An administrator must approve it before you can log in.')
                    else:
                        forms.add_error(None, 'Invalid username or password.')
                except UserModel.DoesNotExist:
                    forms.add_error(None, 'Invalid username or password.')
    context = {
        'form': forms,
        'next': next_url,
        'reg_form': reg_form,
        'staff_guard_form': StaffGuardRegistrationForm(),
        'site_name': 'City College of Bayawan',
    }
    return render(request, 'auth/login.html', context)


@login_required
def profile_edit(request):
    """Edit profile for any authenticated user (admin, guard, staff, faculty). Includes name, email, profile photo; staff/faculty/guard also get extended profile fields."""
    from django.contrib import messages
    from gate.models import StaffGuardProfile, UserProfile

    user = request.user
    profile = getattr(user, 'staff_guard_profile', None)
    has_profile = profile is not None
    user_profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
    current_avatar_url = user_profile.avatar.url if user_profile.avatar else None

    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, request.FILES)
        if form.is_valid():
            user.first_name = (form.cleaned_data.get('first_name') or '').strip()[:150]
            user.last_name = (form.cleaned_data.get('last_name') or '').strip()[:150]
            email = (form.cleaned_data.get('email') or '').strip().lower()
            if email:
                user.email = email
            user.save(update_fields=['first_name', 'last_name', 'email'])
            if has_profile:
                profile.middle_name = (form.cleaned_data.get('middle_name') or '')[:100]
                profile.sex = (form.cleaned_data.get('sex') or '').strip() or ''
                profile.birthdate = form.cleaned_data.get('birthdate')
                profile.address = (form.cleaned_data.get('address') or '')[:500]
                profile.contact_number = (form.cleaned_data.get('contact_number') or '')[:20]
                profile.employee_id = (form.cleaned_data.get('employee_id') or '')[:50]
                profile.department = (form.cleaned_data.get('department') or '')[:150]
                profile.position = (form.cleaned_data.get('position') or '')[:150]
                profile.save(update_fields=[
                    'middle_name', 'sex', 'birthdate', 'address',
                    'contact_number', 'employee_id', 'department', 'position',
                ])
            new_avatar = form.cleaned_data.get('avatar')
            if new_avatar:
                if user_profile.avatar:
                    user_profile.avatar.delete(save=False)
                user_profile.avatar = new_avatar
                user_profile.save(update_fields=['avatar'])
            elif new_avatar is False and user_profile.avatar:
                user_profile.avatar.delete(save=False)
                user_profile.avatar = None
                user_profile.save(update_fields=['avatar'])
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile-edit')
    else:
        initial = {
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'email': user.email or '',
        }
        if has_profile:
            initial.update({
                'middle_name': profile.middle_name or '',
                'sex': profile.sex or '',
                'birthdate': profile.birthdate,
                'address': profile.address or '',
                'contact_number': profile.contact_number or '',
                'employee_id': profile.employee_id or '',
                'department': profile.department or '',
                'position': profile.position or '',
            })
        form = UserProfileEditForm(initial=initial)

    return render(request, 'users/profile_edit.html', {
        'form': form,
        'has_profile': has_profile,
        'current_avatar_url': current_avatar_url,
        'site_name': 'City College of Bayawan',
    })


@login_required
def staff_guard_complete_profile(request):
    """Required one-time profile completion for staff/faculty/guard after first login. Blocks dashboard until filled."""
    from django.contrib import messages
    role = get_user_role(request.user)
    if role not in ('staff', 'faculty', 'guard'):
        return redirect('dashboard')
    profile, _ = StaffGuardProfile.objects.get_or_create(user=request.user, defaults={})
    if profile.profile_complete:
        return redirect('guard-dashboard' if role == 'guard' else 'dashboard')

    if request.method == 'POST':
        form = StaffGuardCompleteProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile.sex = (form.cleaned_data.get('sex') or '').strip()
            profile.birthdate = form.cleaned_data.get('birthdate')
            profile.address = (form.cleaned_data.get('address') or '').strip()[:500]
            profile.contact_number = (form.cleaned_data.get('contact_number') or '').strip()[:20]
            profile.employee_id = (form.cleaned_data.get('employee_id') or '').strip()[:50]
            profile.department = (form.cleaned_data.get('department') or '').strip()[:150]
            profile.position = (form.cleaned_data.get('position') or '').strip()[:150]
            profile.profile_complete = True
            profile.save(update_fields=[
                'sex', 'birthdate', 'address', 'contact_number',
                'employee_id', 'department', 'position', 'profile_complete',
            ])
            avatar_file = form.cleaned_data.get('photo')
            if avatar_file:
                from gate.models import UserProfile
                user_profile, _ = UserProfile.objects.get_or_create(user=request.user, defaults={})
                if user_profile.avatar:
                    user_profile.avatar.delete(save=False)
                user_profile.avatar = avatar_file
                user_profile.save(update_fields=['avatar'])
            messages.success(request, 'Your profile is complete. You now have full access to the dashboard.')
            return redirect('guard-dashboard' if role == 'guard' else 'dashboard')
    else:
        form = StaffGuardCompleteProfileForm(initial={
            'sex': profile.sex or '',
            'birthdate': profile.birthdate,
            'address': profile.address or '',
            'contact_number': profile.contact_number or '',
            'employee_id': profile.employee_id or '',
            'department': profile.department or '',
            'position': profile.position or '',
        })

    return render(request, 'users/staff_guard_complete_profile.html', {
        'form': form,
        'site_name': 'City College of Bayawan',
        'user_role': role,
    })


@login_required
def account_settings(request):
    """Account details (username, email) and change password. For staff, faculty, and guard."""
    from django.contrib import messages
    user = request.user
    role = get_user_role(user)
    # Restrict to staff, faculty, guard so students use their own portal if any
    if role not in ('staff', 'faculty', 'guard'):
        return redirect('profile-edit')
    account_form = AccountDetailsForm(user=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        if request.POST.get('action') == 'save_account':
            account_form = AccountDetailsForm(request.POST, user=user)
            if account_form.is_valid():
                user.username = (account_form.cleaned_data['username'] or '').strip()[:150]
                user.email = (account_form.cleaned_data['email'] or '').strip().lower()
                user.save(update_fields=['username', 'email'])
                messages.success(request, 'Account details saved.')
                return redirect('account-settings')
        elif request.POST.get('action') == 'update_password':
            password_form = PasswordChangeForm(request.POST, user=user)
            account_form = AccountDetailsForm(initial={'username': user.username or '', 'email': user.email or ''}, user=user)
            if password_form.is_valid():
                user.set_password(password_form.cleaned_data['new_password'])
                user.save(update_fields=['password'])
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been updated.')
                return redirect('account-settings')
        else:
            account_form = AccountDetailsForm(request.POST or None, user=user)
            password_form = PasswordChangeForm(request.POST or None, user=user)
    else:
        account_form = AccountDetailsForm(initial={
            'username': user.username or '',
            'email': user.email or '',
        }, user=user)

    return render(request, 'users/account_settings.html', {
        'account_form': account_form,
        'password_form': password_form,
        'site_name': 'City College of Bayawan',
    })


@login_required
def preferences_view(request):
    """Preferences for staff/guard: language, timezone, email notifications for announcements (no SMS)."""
    from django.contrib import messages
    user = request.user
    role = get_user_role(user)
    if role not in ('staff', 'faculty', 'guard'):
        return redirect('profile-edit')
    profile, _ = StaffGuardProfile.objects.get_or_create(user=user, defaults={})
    form = UserPreferencesForm(initial={
        'preferred_language': profile.preferred_language or 'en',
        'preferred_timezone': profile.preferred_timezone or 'Asia/Manila',
        'email_notifications_announcements': profile.email_notifications_announcements,
    })
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST)
        if form.is_valid():
            profile.preferred_language = (form.cleaned_data.get('preferred_language') or 'en')[:10]
            profile.preferred_timezone = (form.cleaned_data.get('preferred_timezone') or 'Asia/Manila')[:63]
            profile.email_notifications_announcements = form.cleaned_data.get('email_notifications_announcements', True)
            profile.save(update_fields=['preferred_language', 'preferred_timezone', 'email_notifications_announcements'])
            messages.success(request, 'Preferences saved.')
            return redirect('preferences')
    return render(request, 'users/preferences.html', {
        'form': form,
        'site_name': 'City College of Bayawan',
    })


def register_page(request):
    """Unified login and registration page."""
    from django.contrib import messages
    from django.contrib.auth.models import Group
    from gate.forms import StudentRegistrationForm
    from gate.models import StaffGuardProfile
    from .forms import LoginForm
    import random
    import string

    # Initialize forms
    login_form = LoginForm()
    reg_form = StudentRegistrationForm()
    staff_guard_form = StaffGuardRegistrationForm()

    def _register_context(extra=None):
        ctx = {
            'form': login_form,
            'reg_form': reg_form,
            'staff_guard_form': staff_guard_form,
            'site_name': 'City College of Bayawan',
            'default_panel': 'register',
        }
        if extra:
            ctx.update(extra)
        return ctx

    if request.method == 'POST':
        # Staff / Faculty / Guard registration (separate form with registration_type=staff_guard)
        if request.POST.get('registration_type') == 'staff_guard':
            staff_guard_form = StaffGuardRegistrationForm(request.POST)
            if staff_guard_form.is_valid():
                from django.contrib.auth import get_user_model
                User = get_user_model()
                role = (staff_guard_form.cleaned_data.get('role') or 'staff').lower()
                username = staff_guard_form.cleaned_data['username']
                email = staff_guard_form.cleaned_data['email']
                password = staff_guard_form.cleaned_data['password']
                first_name = (staff_guard_form.cleaned_data.get('first_name') or '').strip()
                last_name = (staff_guard_form.cleaned_data.get('last_name') or '').strip()
                middle_name = (staff_guard_form.cleaned_data.get('middle_name') or '').strip()
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                )
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                StaffGuardProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'middle_name': middle_name,
                        'profile_complete': False,
                    },
                )
                from gate.admin_notification_service import AdminNotificationService
                role_display = {'staff': 'Staff', 'faculty': 'Faculty', 'guard': 'Guard'}.get(role, role.title())
                AdminNotificationService.notify_staff_guard_registration(user, role_display)
                messages.success(
                    request,
                    'Registration submitted. Your account is pending approval—you can sign in once an administrator activates it.'
                )
                return redirect('login')
            return render(request, 'auth/login.html', _register_context({'default_reg_type': 'staff_guard'}))

        # Login form
        if 'username' in request.POST:  # Login form
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data['username']
                password = login_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    login_form.add_error(None, 'Invalid username or password.')
        
        elif 'last_name' in request.POST:  # Registration form
            # Face registration on mobile sends base64 in POST; form expects a file. Inject photo into FILES before validation.
            reg_files = request.FILES
            face_base64_raw = (request.POST.get('face_photo_base64') or '').strip()
            if face_base64_raw:
                import base64
                from io import BytesIO
                from django.core.files.uploadedfile import InMemoryUploadedFile
                from django.utils.datastructures import MultiValueDict
                try:
                    face_base64 = face_base64_raw.split(',', 1)[1] if ',' in face_base64_raw else face_base64_raw
                    data = base64.b64decode(face_base64)
                    photo_file = InMemoryUploadedFile(
                        BytesIO(data), 'photo', 'face.jpg',
                        'image/jpeg', len(data), None
                    )
                    reg_files = MultiValueDict(request.FILES)
                    reg_files.setlist('photo', [photo_file])
                except Exception:
                    pass  # Let form validate; will show photo error if decode failed
            reg_form = StudentRegistrationForm(request.POST, reg_files)
            if reg_form.is_valid():
                student_id = (reg_form.cleaned_data.get('student_id') or '').strip()
                if not student_id:
                    while True:
                        candidate = 'REG-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                        if not Student.objects.filter(student_id=candidate).exists():
                            student_id = candidate
                            break
                else:
                    if Student.objects.filter(student_id=student_id).exists():
                        reg_form.add_error('student_id', 'This ID number is already registered.')
                        return render(request, 'auth/login.html', _register_context())

                import base64
                from io import BytesIO
                from django.core.files.uploadedfile import InMemoryUploadedFile

                photo = reg_form.cleaned_data.get('photo')
                face_base64 = (request.POST.get('face_photo_base64') or '').strip()
                if face_base64:
                    try:
                        if ',' in face_base64:
                            face_base64 = face_base64.split(',', 1)[1]
                        data = base64.b64decode(face_base64)
                        photo = InMemoryUploadedFile(
                            BytesIO(data), 'photo', 'face.jpg',
                            'image/jpeg', len(data), None
                        )
                    except Exception:
                        reg_form.add_error('photo', 'Invalid face image. Please complete face registration again.')
                        return render(request, 'auth/login.html', _register_context())
                if not photo:
                    reg_form.add_error('photo', 'Please complete face registration using your camera.')
                    return render(request, 'auth/login.html', _register_context())

                from django.core.exceptions import ValidationError
                from gate.forms import validate_student_photo
                from gate.utils import compress_student_photo
                try:
                    validate_student_photo(photo)
                except ValidationError as e:
                    msg = e.messages[0] if e.messages else str(e)
                    reg_form.add_error('photo', msg)
                    return render(request, 'auth/login.html', _register_context())
                if hasattr(photo, 'seek'):
                    photo.seek(0)
                photo = compress_student_photo(photo)

                try:
                    import face_recognition
                    img = face_recognition.load_image_file(photo)
                    locations = face_recognition.face_locations(img)
                    if not locations:
                        reg_form.add_error('photo', 'No face detected. Please upload a clear face photo.')
                        return render(request, 'auth/login.html', _register_context())
                    if len(locations) > 1:
                        reg_form.add_error('photo', 'Multiple faces detected. Please upload a photo with only one person.')
                        return render(request, 'auth/login.html', _register_context())
                except ImportError:
                    pass
                except Exception:
                    reg_form.add_error('photo', 'Could not process the image. Please upload a different photo.')
                    return render(request, 'auth/login.html', _register_context())

                if hasattr(photo, 'seek'):
                    photo.seek(0)

                # Electronic signature (required)
                signature_base64_raw = (request.POST.get('signature_base64') or '').strip()
                sig_file = None
                if signature_base64_raw:
                    import base64
                    from io import BytesIO
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    try:
                        signature_base64 = signature_base64_raw.split(',', 1)[1] if ',' in signature_base64_raw else signature_base64_raw
                        data = base64.b64decode(signature_base64)
                        if len(data) < 100:
                            raise ValueError('Signature too small')
                        sig_file = InMemoryUploadedFile(
                            BytesIO(data), 'signature', 'signature.png',
                            'image/png', len(data), None
                        )
                    except Exception:
                        sig_file = None
                if not sig_file:
                    reg_form.add_error(None, 'Please provide your electronic signature by drawing in the signature box.')
                    return render(request, 'auth/login.html', _register_context())

                email = (reg_form.cleaned_data.get('email') or '').strip().lower()
                if Student.objects.filter(email__iexact=email).exists():
                    reg_form.add_error('email', 'This email address is already registered.')
                    return render(request, 'auth/login.html', _register_context())

                first_name = (reg_form.cleaned_data.get('first_name') or '').strip()
                middle_name = (reg_form.cleaned_data.get('middle_name') or '').strip()
                last_name = (reg_form.cleaned_data.get('last_name') or '').strip()
                sex = (reg_form.cleaned_data.get('sex') or '').strip()

                Student.objects.create(
                    student_id=student_id,
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    email=email,
                    photo=photo,
                    signature=sig_file,
                    address=(reg_form.cleaned_data.get('address') or '').strip(),
                    birthdate=reg_form.cleaned_data.get('birthdate'),
                    sex=sex or '',
                    guardians_parents=(reg_form.cleaned_data.get('guardians_parents') or '').strip(),
                    account_status=Student.ACCOUNT_STATUS_PENDING,
                    is_active=False,
                    course=(reg_form.cleaned_data.get('course') or '').strip() or None,
                    year_level=(reg_form.cleaned_data.get('year_level') or '').strip() or None,
                    section=(reg_form.cleaned_data.get('section') or '').strip() or None,
                    contact_number=(reg_form.cleaned_data.get('contact_number') or '').strip() or None,
                    guardian_contact=(reg_form.cleaned_data.get('guardian_contact') or '').strip() or None,
                )
                messages.success(
                    request,
                    f'Registration submitted. Pending administrator approval. (Ref: {student_id})'
                )
                return redirect('login')

    return render(request, 'auth/login.html', _register_context())

def logout_page(request):
    logout(request)
    return redirect('login')