import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.core.cache import cache
from django.conf import settings as django_settings

from django.contrib.auth.models import User
from gate.models import EventCategory, Event, Student, GateEntry, GateIncident, AuditLog, GuardShift
from gate.gate_views import _granted_visits_count_for_date, _local_day_bounds
from .forms import LoginForm
from .roles import get_user_role, role_required


@require_GET
def privacy_policy(request):
    """Public privacy & data policy page (no login required)."""
    return render(request, 'privacy_policy.html', {
        'site_name': 'City College of Bayawan',
    })


@require_GET
def terms_and_conditions(request):
    """Public terms and conditions page (no login required)."""
    return render(request, 'terms_and_conditions.html', {
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
    return render(request, '404.html', {'site_name': 'City College of Bayawan'}, status=404)


def custom_server_error_view(request):
    """Branded 500 page."""
    return render(request, '500.html', {'site_name': 'City College of Bayawan'}, status=500)


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
    return render(request, 'user_list.html', {
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
    return render(request, 'dashboard.html', context)


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
                role = get_user_role(user)
                if role is None:
                    messages.error(request, 'Your account has no role (Admin, Faculty, Staff, or Guard). Contact the administrator.')
                    return render(request, 'login.html', {
                        'form': forms, 'next': next_url, 'reg_form': reg_form,
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
                redirect_to = request.POST.get('next') or request.GET.get('next')
                if role == 'guard':
                    # Guards always go to guard dashboard after login (never gate-scan)
                    redirect_to = 'guard-dashboard'
                elif not redirect_to:
                    redirect_to = 'dashboard'
                return redirect(redirect_to)
            else:
                forms.add_error(None, 'Invalid ID number or password.')
    context = {
        'form': forms,
        'next': next_url,
        'reg_form': reg_form,
        'site_name': 'City College of Bayawan',
    }
    return render(request, 'login.html', context)


def register_page(request):
    """Unified login and registration page."""
    from django.contrib import messages
    from gate.forms import StudentRegistrationForm
    from .forms import LoginForm
    import random
    import string

    # Initialize forms
    login_form = LoginForm()
    reg_form = StudentRegistrationForm()

    if request.method == 'POST':
        # Check which form was submitted
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
                        return render(request, 'login.html', {
                            'form': login_form,
                            'reg_form': reg_form,
                            'site_name': 'City College of Bayawan',
                            'default_panel': 'register',
                        })

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
                        return render(request, 'login.html', {
                            'form': login_form,
                            'reg_form': reg_form,
                            'site_name': 'City College of Bayawan',
                            'default_panel': 'register',
                        })
                if not photo:
                    reg_form.add_error('photo', 'Please complete face registration using your camera.')
                    return render(request, 'login.html', {
                        'form': login_form,
                        'reg_form': reg_form,
                        'site_name': 'City College of Bayawan',
                        'default_panel': 'register',
                    })

                from django.core.exceptions import ValidationError
                from gate.forms import validate_student_photo
                from gate.utils import compress_student_photo
                try:
                    validate_student_photo(photo)
                except ValidationError as e:
                    msg = e.messages[0] if e.messages else str(e)
                    reg_form.add_error('photo', msg)
                    return render(request, 'login.html', {
                        'form': login_form,
                        'reg_form': reg_form,
                        'site_name': 'City College of Bayawan',
                        'default_panel': 'register',
                    })
                if hasattr(photo, 'seek'):
                    photo.seek(0)
                photo = compress_student_photo(photo)

                try:
                    import face_recognition
                    img = face_recognition.load_image_file(photo)
                    locations = face_recognition.face_locations(img)
                    if not locations:
                        reg_form.add_error('photo', 'No face detected. Please upload a clear face photo.')
                        return render(request, 'login.html', {
                            'form': login_form,
                            'reg_form': reg_form,
                            'site_name': 'City College of Bayawan',
                            'default_panel': 'register',
                        })
                    if len(locations) > 1:
                        reg_form.add_error('photo', 'Multiple faces detected. Please upload a photo with only one person.')
                        return render(request, 'login.html', {
                            'form': login_form,
                            'reg_form': reg_form,
                            'site_name': 'City College of Bayawan',
                            'default_panel': 'register',
                        })
                except ImportError:
                    pass
                except Exception:
                    reg_form.add_error('photo', 'Could not process the image. Please upload a different photo.')
                    return render(request, 'login.html', {
                        'form': login_form,
                        'reg_form': reg_form,
                        'site_name': 'City College of Bayawan',
                        'default_panel': 'register',
                    })

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
                    return render(request, 'login.html', {
                        'form': login_form,
                        'reg_form': reg_form,
                        'site_name': 'City College of Bayawan',
                        'default_panel': 'register',
                    })

                email = (reg_form.cleaned_data.get('email') or '').strip().lower()
                if Student.objects.filter(email__iexact=email).exists():
                    reg_form.add_error('email', 'This email address is already registered.')
                    return render(request, 'login.html', {
                        'form': login_form,
                        'reg_form': reg_form,
                        'site_name': 'City College of Bayawan',
                        'default_panel': 'register',
                    })

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

    return render(request, 'login.html', {
        'form': login_form,
        'reg_form': reg_form,
        'site_name': 'City College of Bayawan',
        'default_panel': 'register',
    })

def logout_page(request):
    logout(request)
    return redirect('login')