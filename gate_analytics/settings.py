"""
Django settings for Gate Entry Monitoring & Data Analytics (City College of Bayawan).
"""
import os

# Load .env from project root so it's found regardless of current working directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_path = os.path.join(BASE_DIR, '.env')
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    # Fallback: simple .env parser so DB/email config still works even without python-dotenv.
    if os.path.exists(_env_path):
        with open(_env_path, encoding='utf-8') as f:
            for _line in f:
                line = _line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Do not overwrite existing environment variables.
                os.environ.setdefault(key, value)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'gvv(&d^k0f5^xgqa+#ct4sxcg5%&5q&k2d(!uek5m+qj#b^0#2')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# CSRF Trusted Origins (for AJAX requests)
CSRF_TRUSTED_ORIGINS = [
    # ngrok tunnel URLs change often (trial/subdomain). Trust any ngrok host via wildcard.
    # Django expects full origins with scheme for CSRF trusted origins.
    'https://*.ngrok-free.dev',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
]

# Host header validation. For local dev + LAN + ngrok/tunnels, use '*' (only safe with DEBUG=True).
# Production: set DJANGO_ALLOWED_HOSTS=example.com,www.example.com (comma-separated, no spaces needed)
# or rely on the non-DEBUG list below. Never use '*' when DEBUG=False.

ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        '192.168.180.160',
        '192.168.1.81',
        '192.168.181.146',
        '192.168.254.105',
        '192.168.181.120',
        '172.20.10.2',
        '192.168.254.125',
        '10.0.1.186',
        '192.168.180.135',
        'unsurrendering-implacably-alfreda.ngrok-free.dev',
        '.ngrok-free.app',
        '.ngrok-free.dev',
        '.ngrok.io',
    ]



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party apps
    'crispy_forms',
    'mapbox_location_field',
    'ckeditor',
    'ckeditor_uploader',
    'betterforms',

    # Local apps
    'gate.apps.GateConfig',
]

MIDDLEWARE = [
    'gate_analytics.middleware.BlockedIPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'gate_analytics.middleware.NgrokCsrfTrustMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'gate_analytics.middleware.StaffPersonnelCompleteProfileMiddleware',
    'gate_analytics.middleware.LanguageFromProfileMiddleware',
    'gate_analytics.middleware.SessionTimeoutMiddleware',
    'gate_analytics.middleware.NoCacheAuthMiddleware',
    'gate_analytics.middleware.GateEntryMySQLFixMiddleware',
    'gate_analytics.notification_middleware.NotificationReadMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Optional: restrict /admin/ and /login/ by IP (set ALLOWED_ADMIN_IPS = ['1.2.3.4'] or ['10.0.0.0/8'])
    # 'gate_analytics.middleware.IPAllowlistMiddleware',
]

ROOT_URLCONF = 'gate_analytics.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'gate_analytics.roles.user_role_context',
                'gate_analytics.context_processors.notifications_context',
                'gate_analytics.context_processors.gate_notifications_context',
                'gate_analytics.context_processors.theme_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'gate_analytics.wsgi.application'

# Session: auto-logout after inactivity. Admin/dashboard use SESSION_COOKIE_AGE; gate scan uses 15 min (SessionTimeoutMiddleware).
# Set SESSION_COOKIE_AGE in .env (seconds), e.g. 1800=30 min, 3600=1 hr. Default 30 min.
SESSION_SAVE_EVERY_REQUEST = True  # Reset inactivity timer on every request
_session_age = os.environ.get('SESSION_COOKIE_AGE', '1800')
SESSION_COOKIE_AGE = int(_session_age) if str(_session_age).isdigit() else 1800
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_HTTPONLY = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# When using ngrok HTTPS (or any HTTPS reverse proxy), set NGROK_HTTPS_COOKIES=1 in .env so
# session/csrf cookies are marked Secure (some browsers require this on https://*.ngrok URLs).
if os.environ.get('NGROK_HTTPS_COOKIES', '').lower() in ('1', 'true', 'yes'):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGIN_URL = '/login/'

# Upload limits: registration form has photo + signature; mobile cameras can send 3–5 MB+
# Default is 2.5 MB, which causes RequestDataTooBig on phone registration.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# Set DB_ENGINE in .env: sqlite (default), mysql, or postgresql.
# On Windows/XAMPP use 127.0.0.1 (IPv4); avoid "localhost" which may resolve to IPv6.

_db_engine = os.environ.get('DB_ENGINE', 'sqlite').lower().strip()
if _db_engine == 'mysql':
    _db_host = (os.environ.get('DB_HOST') or '127.0.0.1').strip() or '127.0.0.1'
    _db_port = os.environ.get('DB_PORT', '3306')
    try:
        _db_port = int(_db_port)
    except (TypeError, ValueError):
        _db_port = 3306
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'gate_analytics'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': _db_host,
            'PORT': _db_port,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'connect_timeout': 10,
            },
        }
    }
elif _db_engine in ('postgresql', 'postgres'):
    _db_host = (os.environ.get('DB_HOST') or '127.0.0.1').strip() or '127.0.0.1'
    _db_port = os.environ.get('DB_PORT', '5432')
    try:
        _db_port = int(_db_port)
    except (TypeError, ValueError):
        _db_port = 5432
    DATABASES = {
        'default': {
            'ENGINE': 'gate_analytics.postgresql_utc',
            'NAME': os.environ.get('DB_NAME', 'gate_analytics_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': _db_host,
            'PORT': _db_port,
            'OPTIONS': {
                'connect_timeout': 10,
                'options': '-c timezone=UTC',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en'

TIME_ZONE = 'Asia/Manila'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Languages for staff/guard/faculty preferences (English / Filipino)
LANGUAGES = [
    ('en', 'English'),
    ('fil', 'Filipino'),
]

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Media files (Images)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Crsipy forms
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Mapbox key (set MAPBOX_KEY in .env; never commit a real token to git)
MAPBOX_KEY = os.environ.get('MAPBOX_KEY', '')

# Ckeditor config
CKEDITOR_JQUERY_URL = 'https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

CKEDITOR_UPLOAD_PATH = "event-details/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': [
            ['Bold', 'Italic', 'Underline', 'TextColor', 'BGColor'],
        ],
    },
}

# Cache for dashboard counts (1–2 min TTL). Use LocMem if no Redis/Memcached.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'gate-analytics-default',
        'OPTIONS': {'MAX_ENTRIES': 500},
    }
}
CACHE_DASHBOARD_SECONDS = 120  # 2 minutes

# After login, if the user did not open /login/?next=...
# — Staff / Faculty / Supervisor: default landing page (set to 'dashboard'; use 'gate-scan' to open scanner first).
# — Admin default: LOGIN_REDIRECT_DEFAULT_ADMIN.
# Physical guards do not log in; staff open /gate/ from the dashboard when needed.
LOGIN_REDIRECT_GATE_FIRST_ROLES = ('staff', 'faculty', 'supervisor')
LOGIN_REDIRECT_DEFAULT_GATE_STAFF = 'dashboard'
LOGIN_REDIRECT_DEFAULT_ADMIN = 'dashboard'

# Optional: API token for read-only attendance integration (set API_ATTENDANCE_TOKEN in env)
API_ATTENDANCE_TOKEN = os.environ.get('API_ATTENDANCE_TOKEN', '')

# Guard wall display: shared secret for /gate/guard-display/ and /gate/api/guard-dashboard/ (no login).
# Staff gate scanner POSTs heartbeats; display shows "scanner active" while heartbeats arrive within TTL.
GATE_GUARD_DISPLAY_TOKEN = os.environ.get('GATE_GUARD_DISPLAY_TOKEN', '')
GATE_SCANNER_HEARTBEAT_TTL = int(os.environ.get('GATE_SCANNER_HEARTBEAT_TTL', '90'))
# Daily gate: minimum time between duplicate scans (same direction) while still inside / outside (minutes).
try:
    _gate_cool = int(os.environ.get('GATE_SCAN_REPEAT_COOLDOWN_MINUTES', '5'))
except (TypeError, ValueError):
    _gate_cool = 5
GATE_SCAN_REPEAT_COOLDOWN_MINUTES = max(1, min(_gate_cool, 24 * 60))
# Daily gate: global = wait GATE_SCAN_REPEAT_COOLDOWN_MINUTES after any scan before the next (recommended).
# same_direction = only block duplicate IN or duplicate OUT (allows immediate IN↔OUT alternation when UI auto-suggests).
_raw_gate_cool_scope = (os.environ.get('GATE_SCAN_REPEAT_COOLDOWN_SCOPE', 'global') or '').strip().lower()
GATE_SCAN_REPEAT_COOLDOWN_SCOPE = _raw_gate_cool_scope if _raw_gate_cool_scope in ('global', 'same_direction') else 'global'
# Guard scan-success popup layout: split (photo | text), poster (photo banner on top), idcard (photo + bordered info panel)
_raw_guard_popup = (os.environ.get('GATE_GUARD_STUDENT_POPUP_STYLE', 'split') or '').strip().lower()
GATE_GUARD_STUDENT_POPUP_STYLE = _raw_guard_popup if _raw_guard_popup in ('split', 'poster', 'idcard') else 'split'
# Optional: user id for GateEntry.recorded_by when using token-only /gate/embed-scanner/ (guard monitor).
GATE_GUARD_EMBED_RECORDED_BY_USER_ID = os.environ.get('GATE_GUARD_EMBED_RECORDED_BY_USER_ID', '') or None
if GATE_GUARD_EMBED_RECORDED_BY_USER_ID:
    try:
        GATE_GUARD_EMBED_RECORDED_BY_USER_ID = int(GATE_GUARD_EMBED_RECORDED_BY_USER_ID)
    except ValueError:
        GATE_GUARD_EMBED_RECORDED_BY_USER_ID = None
else:
    GATE_GUARD_EMBED_RECORDED_BY_USER_ID = None

# Guard embed: "Report incident" → GateIncident + notify office groups (Django Group names, comma-separated)
# id_issue → SAS; not_registered → Registrar; other → both. Optional direct emails always get mail.
GATE_GUARD_INCIDENT_GROUPS_SAS = os.environ.get(
    'GATE_GUARD_INCIDENT_GROUPS_SAS',
    'Student Affairs,SAS',
)
GATE_GUARD_INCIDENT_GROUPS_REGISTRAR = os.environ.get(
    'GATE_GUARD_INCIDENT_GROUPS_REGISTRAR',
    'Registrar',
)
GATE_GUARD_INCIDENT_EMAILS_SAS = os.environ.get('GATE_GUARD_INCIDENT_EMAILS_SAS', '')
GATE_GUARD_INCIDENT_EMAILS_REGISTRAR = os.environ.get('GATE_GUARD_INCIDENT_EMAILS_REGISTRAR', '')
GATE_GUARD_INCIDENT_FALLBACK_BROADCAST = os.environ.get(
    'GATE_GUARD_INCIDENT_FALLBACK_BROADCAST', 'true'
).lower() in ('1', 'true', 'yes')

# Notifications (email)
NOTIFICATION_EMAILS = os.environ.get('NOTIFICATION_EMAILS', '').split(',') if os.environ.get('NOTIFICATION_EMAILS') else []
NOTIFY_ON_DENIED_ENTRY = os.environ.get('NOTIFY_ON_DENIED_ENTRY', 'false').lower() in ('1', 'true', 'yes')
NOTIFY_ON_CAPACITY_ALERT = os.environ.get('NOTIFY_ON_CAPACITY_ALERT', 'true').lower() in ('1', 'true', 'yes')

# Email backend / sender (students, staff, guards)
# - By default, emails are printed to the console for local development.
# - To actually send emails (e.g. via Gmail), set EMAIL_* vars in .env.
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25') or '25')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
_email_host_password = os.environ.get('EMAIL_HOST_PASSWORD', '')
# App passwords from Google are often shown with spaces; strip them just in case.
EMAIL_HOST_PASSWORD = _email_host_password.replace(' ', '') if _email_host_password else ''
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@example.com')
SITE_NAME = os.environ.get('SITE_NAME', 'City College of Bayawan')