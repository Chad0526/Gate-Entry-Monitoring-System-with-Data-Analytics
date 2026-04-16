"""Session flag for a softer post-login dashboard loader (one paint only)."""
SESSION_KEY_POST_LOGIN_LOADER = 'ccb_post_login_loader'


def mark_post_login_loader_if_dashboard(request, redirect_to):
    """
    Set session flag when redirect target is the main dashboard or gate analytics.
    Used after successful login so base.html can style the first load differently.
    """
    from django.shortcuts import resolve_url
    from urllib.parse import urlparse

    try:
        target = urlparse(resolve_url(redirect_to)).path.rstrip('/') or '/'
        for name in ('dashboard', 'gate-analytics'):
            p = urlparse(resolve_url(name)).path.rstrip('/') or '/'
            if target == p:
                request.session[SESSION_KEY_POST_LOGIN_LOADER] = True
                return
    except Exception:
        pass


def pop_post_login_loader(request):
    """Return True once after login→dashboard redirect; clears the session key."""
    return bool(request.session.pop(SESSION_KEY_POST_LOGIN_LOADER, False))
