"""Optional IP allowlist for admin and login. Set ALLOWED_ADMIN_IPS in settings (list of IPs or CIDR)."""
from django.conf import settings as django_settings
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import LANGUAGE_SESSION_KEY, activate


def _origin_from_request(request):
    origin = request.META.get('HTTP_ORIGIN')
    if origin:
        return origin.rstrip('/')
    referer = request.META.get('HTTP_REFERER')
    if referer:
        from urllib.parse import urlparse
        p = urlparse(referer)
        if p.scheme and p.netloc:
            return f'{p.scheme}://{p.netloc}'
    return None


def _ngrok_origin_from_forwarded_host(request):
    """Build https://<host> when ngrok forwards Host but Origin is missing (common on GET)."""
    host = (request.META.get('HTTP_X_FORWARDED_HOST') or '').split(',')[0].strip()
    if not host:
        host = (request.META.get('HTTP_HOST') or '').split(':')[0]
    else:
        host = host.split(':')[0]
    if not host or 'ngrok' not in host.lower():
        return None
    proto = (request.META.get('HTTP_X_FORWARDED_PROTO') or '').split(',')[0].strip().lower()
    if proto not in ('http', 'https'):
        proto = 'https' if request.is_secure() else (
            'https' if ('ngrok-free' in host or 'ngrok.app' in host) else 'http'
        )
    return f'{proto}://{host}'


# Headers to prevent caching of authenticated pages (stops back button showing dashboard after logout)
NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    'Pragma': 'no-cache',
    'Expires': '0',
}


class StaffPersonnelCompleteProfileMiddleware(MiddlewareMixin):
    """Redirect staff/faculty users to complete-profile until they have filled required profile (after first login)."""
    def process_request(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None
        path = (request.path or '').rstrip('/')
        # Allow gate JSON APIs to work before staff profile completion (heartbeat, dashboard polling, etc.)
        skip_prefixes = ('/profile/complete', '/logout', '/static', '/media', '/admin', '/login', '/gate/api')
        if any(path == p or path.startswith(p + '/') for p in skip_prefixes):
            return None
        if path in ('', '/') or path == '/login':
            return None
        try:
            from gate_analytics.roles import get_user_role
            from gate.models import StaffPersonnelProfile
            role = get_user_role(request.user)
            if role not in ('staff', 'faculty'):
                return None
            profile, _ = StaffPersonnelProfile.objects.get_or_create(
                user=request.user, defaults={'profile_complete': False}
            )
            if getattr(profile, 'profile_complete', False):
                return None
            return HttpResponseRedirect(reverse('staff-personnel-complete-profile'))
        except Exception:
            return None


class LanguageFromProfileMiddleware(MiddlewareMixin):
    """For staff/faculty, set session language from StaffPersonnelProfile.preferred_language."""
    def process_request(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return None
        try:
            from gate_analytics.roles import get_user_role
            from gate.models import StaffPersonnelProfile
            role = get_user_role(request.user)
            if role not in ('staff', 'faculty'):
                return None
            profile = StaffPersonnelProfile.objects.filter(user=request.user).first()
            if not profile or not getattr(profile, 'preferred_language', None):
                return None
            lang = (profile.preferred_language or '').strip() or 'en'
            if lang not in ('en', 'fil'):
                lang = 'en'
            request.session[LANGUAGE_SESSION_KEY] = lang
            activate(lang)
        except Exception:
            pass
        return None


class SessionTimeoutMiddleware(MiddlewareMixin):
    """Auto-logout after inactivity: shorter expiry on gate scan (devices left unattended). Admin/dashboard use SESSION_COOKIE_AGE (e.g. 30 min)."""
    GATE_SCAN_EXPIRY = 900  # 15 minutes for any /gate/ path (scan UI)
    def process_request(self, request):
        path = (request.path or '').rstrip('/')
        if path == '/gate' or path.startswith('/gate/'):
            request.session.set_expiry(self.GATE_SCAN_EXPIRY)
        return None


class NoCacheAuthMiddleware(MiddlewareMixin):
    """Prevent caching of pages served to authenticated users so back button doesn't show dashboard after logout."""
    def process_response(self, request, response):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            if response.get('Content-Type', '').split(';')[0].strip().lower() == 'text/html':
                for key, value in NO_CACHE_HEADERS.items():
                    response[key] = value
        return response


class NgrokCsrfTrustMiddleware(MiddlewareMixin):
    """When request comes via ngrok, add its Origin (or Host-derived URL) to CSRF_TRUSTED_ORIGINS so login and forms work."""
    def process_request(self, request):
        origin = _origin_from_request(request)
        if not origin or 'ngrok' not in origin.lower():
            origin = _ngrok_origin_from_forwarded_host(request)
        if not origin or 'ngrok' not in origin.lower():
            return None
        trusted = getattr(django_settings, 'CSRF_TRUSTED_ORIGINS', None) or []
        if isinstance(trusted, list) and origin not in trusted:
            trusted = list(trusted) + [origin]
            setattr(django_settings, 'CSRF_TRUSTED_ORIGINS', trusted)
        return None

# One-time fix: add gate_gateentry.out_reason_code on MySQL if missing (so gate/entries and save_scan work).
# PostgreSQL and SQLite: schema is handled by migrations (0036/0037); this is a no-op.
_gate_entry_column_checked = False


def ensure_out_reason_code_column():
    global _gate_entry_column_checked
    if _gate_entry_column_checked:
        return
    from django.db import connection
    # PostgreSQL and SQLite: migrations already add the column; skip.
    if connection.vendor in ('postgresql', 'sqlite'):
        _gate_entry_column_checked = True
        return
    if connection.vendor != 'mysql':
        _gate_entry_column_checked = True
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'gate_gateentry' AND COLUMN_NAME = 'out_reason_code'
            """)
            if cursor.fetchone()[0] > 0:
                _gate_entry_column_checked = True
                return
            cursor.execute("ALTER TABLE gate_gateentry ADD COLUMN out_reason_code VARCHAR(32) NOT NULL DEFAULT ''")
            try:
                cursor.execute("CREATE INDEX gate_gateentry_out_reason_code_idx ON gate_gateentry (out_reason_code)")
            except Exception:
                pass
    except Exception:
        pass
    _gate_entry_column_checked = True


class GateEntryMySQLFixMiddleware(MiddlewareMixin):
    """On first request with MySQL, add out_reason_code to gate_gateentry if missing. No-op for PostgreSQL/SQLite (migrations handle schema)."""
    def process_request(self, request):
        if request.path.startswith('/gate/'):
            ensure_out_reason_code_column()
        return None


def _get_client_ip(request):
    """Extract client IP from request, respecting X-Forwarded-For for proxied setups."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
    return xff or request.META.get('REMOTE_ADDR', '')


class BlockedIPMiddleware(MiddlewareMixin):
    """Reject requests from IPs stored in gate.BlockedIP (is_active=True). Uses in-memory cache refreshed every 30s."""
    _cache = set()
    _last_refresh = 0

    def process_request(self, request):
        import time
        now = time.time()
        if now - BlockedIPMiddleware._last_refresh > 30:
            try:
                from gate.models import BlockedIP
                BlockedIPMiddleware._cache = set(
                    BlockedIP.objects.filter(is_active=True).values_list('ip_address', flat=True)
                )
            except Exception:
                BlockedIPMiddleware._cache = set()
            BlockedIPMiddleware._last_refresh = now

        ip = _get_client_ip(request)
        if ip and ip in BlockedIPMiddleware._cache:
            try:
                from gate.models import BlockedIP
                from django.db.models import F
                BlockedIP.objects.filter(ip_address=ip, is_active=True).update(
                    failed_attempts=F('failed_attempts') + 1
                )
            except Exception:
                pass
            return HttpResponseForbidden(
                '<html><body style="font-family:Inter,sans-serif;display:flex;align-items:center;'
                'justify-content:center;min-height:100vh;background:#fef2f2;color:#991b1b;">'
                '<div style="text-align:center;max-width:480px;">'
                '<h1 style="font-size:3rem;margin:0;">403</h1>'
                '<h2 style="margin:8px 0;">Access Denied</h2>'
                '<p style="color:#b91c1c;">Your IP address has been blocked due to suspicious activity. '
                'Contact the system administrator if you believe this is an error.</p>'
                '</div></body></html>'
            )
        return None

    @classmethod
    def clear_cache(cls):
        cls._cache = set()
        cls._last_refresh = 0


class IPAllowlistMiddleware(MiddlewareMixin):
    """Restrict /admin/ and /login/ to allowed IPs when ALLOWED_ADMIN_IPS is set."""
    def process_request(self, request):
        allowed = getattr(django_settings, 'ALLOWED_ADMIN_IPS', None)
        if not allowed:
            return None
        path = request.path.lstrip('/')
        if not (path.startswith('admin/') or path == 'login' or path == 'admin'):
            return None
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
        if not ip:
            return None
        if isinstance(allowed, (list, tuple)):
            if ip in allowed:
                return None
            # Optional: support CIDR via ipaddress module
            try:
                import ipaddress
                net = ipaddress.ip_address(ip)
                for a in allowed:
                    if '/' in str(a):
                        if net in ipaddress.ip_network(a, strict=False):
                            return None
                    elif ip == a:
                        return None
            except Exception:
                pass
        return HttpResponseForbidden('Access restricted by IP.')
