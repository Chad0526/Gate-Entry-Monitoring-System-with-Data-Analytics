"""
Production settings for Gate Entry Monitoring & Data Analytics (City College of Bayawan).
CRITICAL: Use this file for production deployment only.
"""
from .settings import *
import os

# ==============================================================================
# SECURITY SETTINGS (CRITICAL)
# ==============================================================================

# SECURITY WARNING: Use environment variable for secret key
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'CHANGE-THIS-IN-PRODUCTION')

# SECURITY WARNING: Set to False in production
DEBUG = False

# Add your production domain here
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ==============================================================================
# HTTPS & SECURITY HEADERS
# ==============================================================================

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# SAMEORIGIN: e-ID card previews use same-site iframes; DENY would show a blank/broken iframe.
X_FRAME_OPTIONS = 'SAMEORIGIN'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF Trusted Origins (for AJAX requests)
CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]

# ==============================================================================
# DATABASE (PRODUCTION - Use PostgreSQL or MySQL)
# ==============================================================================

# Option 1: PostgreSQL (Recommended)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'gate_analytics_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,  # CRITICAL: Ensures transaction.atomic works
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Option 2: MySQL (Alternative)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.environ.get('DB_NAME', 'gate_analytics_db'),
#         'USER': os.environ.get('DB_USER', 'root'),
#         'PASSWORD': os.environ.get('DB_PASSWORD', ''),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '3306'),
#         'ATOMIC_REQUESTS': True,
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#             'charset': 'utf8mb4',
#         }
#     }
# }

# ==============================================================================
# STATIC & MEDIA FILES (PRODUCTION)
# ==============================================================================

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# For cloud storage (optional, if using AWS S3 or similar):
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')

# ==============================================================================
# LOGGING (PRODUCTION)
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django_errors.log'),
            'formatter': 'verbose',
        },
        'attendance_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/attendance.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'gate.gate_views': {
            'handlers': ['attendance_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ==============================================================================
# SESSION & COOKIE SETTINGS
# ==============================================================================

SESSION_COOKIE_AGE = 43200  # 12 hours (guards stay logged in for full shift)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True

# ==============================================================================
# EMAIL SETTINGS (for notifications, optional)
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@yourdomain.com')

# ==============================================================================
# PERFORMANCE SETTINGS
# ==============================================================================

# Connection pooling (for PostgreSQL)
CONN_MAX_AGE = 600

# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# ==============================================================================
# DEPLOYMENT NOTES
# ==============================================================================

# Before deploying:
# 1. Set environment variables in .env file
# 2. Run: python manage.py migrate --settings=gate_analytics.settings_prod
# 3. Run: python manage.py collectstatic --settings=gate_analytics.settings_prod
# 4. Create superuser: python manage.py createsuperuser --settings=gate_analytics.settings_prod
# 5. Test: python manage.py check --settings=gate_analytics.settings_prod
# 6. Deploy with Gunicorn + Nginx

# Start server:
# gunicorn gate_analytics.wsgi:application \
#   --env DJANGO_SETTINGS_MODULE=gate_analytics.settings_prod \
#   --bind 0.0.0.0:8000 --workers 4 --daemon
