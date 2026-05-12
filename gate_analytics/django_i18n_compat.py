"""Django 5.0+ no longer exports LANGUAGE_SESSION_KEY from django.utils.translation."""

try:
    from django.utils.translation import LANGUAGE_SESSION_KEY
except ImportError:  # Django 5+
    LANGUAGE_SESSION_KEY = '_language'
