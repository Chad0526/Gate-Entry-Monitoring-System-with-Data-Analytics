"""
django-betterforms 1.2 targets Django 1.x and imports APIs removed in Django 3.0+.

This runs from settings.py before URL loading imports ``betterforms``.
"""
import sys

import six


def apply_django_betterforms_compat():
    # django.utils.six was removed in Django 3; betterforms uses string_types, iteritems, etc.
    if 'django.utils.six' not in sys.modules:
        sys.modules['django.utils.six'] = six
        # ``from django.utils.six.moves import reduce`` looks up this submodule in sys.modules.
        sys.modules['django.utils.six.moves'] = six.moves

    from django.utils import encoding as django_encoding

    if not hasattr(django_encoding, 'python_2_unicode_compatible'):

        def python_2_unicode_compatible(klass):
            return klass

        django_encoding.python_2_unicode_compatible = python_2_unicode_compatible
