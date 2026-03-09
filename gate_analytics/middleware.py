"""Optional IP allowlist for admin and login. Set ALLOWED_ADMIN_IPS in settings (list of IPs or CIDR)."""
from django.conf import settings as django_settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin


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


# Headers to prevent caching of authenticated pages (stops back button showing dashboard after logout)
NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    'Pragma': 'no-cache',
    'Expires': '0',
}


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
    """When request comes via ngrok, add its Origin to CSRF_TRUSTED_ORIGINS so login and forms work."""
    def process_request(self, request):
        origin = _origin_from_request(request)
        if not origin or 'ngrok' not in origin:
            return None
        trusted = getattr(django_settings, 'CSRF_TRUSTED_ORIGINS', None) or []
        if isinstance(trusted, list) and origin not in trusted:
            trusted = list(trusted) + [origin]
            setattr(django_settings, 'CSRF_TRUSTED_ORIGINS', trusted)
        return None

# One-time fix: add gate_gateentry.out_reason_code on MySQL if missing (so gate/entries and save_scan work)
_gate_entry_column_checked = False


def ensure_out_reason_code_column():
    global _gate_entry_column_checked
    if _gate_entry_column_checked:
        return
    from django.db import connection
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
    """On first request with MySQL, add out_reason_code to gate_gateentry if missing."""
    def process_request(self, request):
        if request.path.startswith('/gate/'):
            ensure_out_reason_code_column()
        return None


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
