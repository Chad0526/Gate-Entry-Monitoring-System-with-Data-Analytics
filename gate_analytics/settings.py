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
    pass  # python-dotenv not installed; use system env or SQLite

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'gvv(&d^k0f5^xgqa+#ct4sxcg5%&5q&k2d(!uek5m+qj#b^0#2'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# CSRF Trusted Origins (for AJAX requests)
CSRF_TRUSTED_ORIGINS = [
    'https://unsurrendering-implacably-alfreda.ngrok-free.dev',
    '.ngrok-free.app',
    '.ngrok-free.dev',
    '.ngrok.io',

]


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
    # Any ngrok URL (subdomains allowed)
    'unsurrendering-implacably-alfreda.ngrok-free.dev ',
    '.ngrok-free.app',
    '.ngrok-free.dev',
    '.ngrok.io',
]

# Ngrok / tunnel: allow forms (CSRF) and redirects from the public URL
_ngrok_host = os.environ.get('NGROK_HOST', '').strip()
CSRF_TRUSTED_ORIGINS = []
if _ngrok_host:
    _ngrok_origin = f'https://{_ngrok_host}' if not _ngrok_host.startswith('http') else _ngrok_host
    CSRF_TRUSTED_ORIGINS = [_ngrok_origin.rstrip('/')]
# When behind ngrok, the request to Django is often HTTP; trust X-Forwarded-Proto so links use HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True


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
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'gate_analytics.middleware.NgrokCsrfTrustMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
                'gate_analytics.context_processors.theme_context',
                'gate_analytics.context_processors.guard_notifications_context',
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
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
# Set DB_ENGINE=mysql in .env to use MySQL; otherwise SQLite is used.
# On Windows/XAMPP use 127.0.0.1 (IPv4); avoid "localhost" which may resolve to IPv6.

_db_engine = os.environ.get('DB_ENGINE', 'sqlite').lower()
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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Manila'

USE_I18N = True

USE_L10N = True

USE_TZ = True


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

# Mapbox key define (use environment variable for security)
MAPBOX_KEY = os.environ.get('MAPBOX_KEY', '')

# Ckeditor config
CKEDITOR_JQUERY_URL = 'https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

CKEDITOR_UPLOAD_PATH = "event-details/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': None,
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

# Optional: API token for read-only attendance integration (set API_ATTENDANCE_TOKEN in env)
API_ATTENDANCE_TOKEN = os.environ.get('API_ATTENDANCE_TOKEN', '')

# Notifications (email)
NOTIFICATION_EMAILS = os.environ.get('NOTIFICATION_EMAILS', '').split(',') if os.environ.get('NOTIFICATION_EMAILS') else []
NOTIFY_ON_DENIED_ENTRY = os.environ.get('NOTIFY_ON_DENIED_ENTRY', 'false').lower() in ('1', 'true', 'yes')
NOTIFY_ON_CAPACITY_ALERT = os.environ.get('NOTIFY_ON_CAPACITY_ALERT', 'true').lower() in ('1', 'true', 'yes')