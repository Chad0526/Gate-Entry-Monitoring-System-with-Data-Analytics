# Exposing the app with ngrok (troubleshooting)

## Quick checks

1. **Django must be running** on the same PC as ngrok, bound to all interfaces:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   Or use `runserver_global.bat` in the project root.

2. **ngrok must forward to that port** (example for port 8000):
   ```bash
   ngrok http 8000
   ```

3. **Verify locally first** (same machine):
   - `http://127.0.0.1:8000/login/` — login page should load.
   - `http://127.0.0.1:8000/health/` — should return plain text `ok`.

4. **Then via the public URL** (replace with your ngrok host):
   - `https://YOUR-SUBDOMAIN.ngrok-free.dev/health/` — should return `ok`.
   - If `health` works but `/` does not, compare the **Network** tab in DevTools (status code, response size).

## Blank white page in the browser

### A. ngrok “browser warning” (free tier)

The first time you open an ngrok URL in a normal browser, ngrok may show an **interstitial** page (“You are about to visit…”) and a **Visit Site** button. If scripts or cookies are blocked, the page can look broken or empty.

- Click **Visit Site** if you see it.
- Try another browser or **InPrivate/Incognito** mode.
- Disable extensions that block third-party scripts or cookies.

Automated tools (curl, Postman) can send the header `ngrok-skip-browser-warning: true` on the **request** to ngrok; that does not apply to a normal browser click.

### B. Tunnel or server not running

If ngrok is stopped or Django is not listening on the port ngrok uses, the browser may show an empty or minimal error view depending on the browser.

- Restart: Django first, then ngrok.
- Confirm ngrok’s **Forwarding** line matches your Django port (e.g. `http://localhost:8000`).

### C. Windows Firewall

The first time Python binds to `0.0.0.0`, Windows may block inbound connections. Allow **Python** on **private** networks so LAN and ngrok (which connects to localhost) work as expected.

### D. Django URL / auth confusion (fixed in project)

`django.contrib.auth.urls` was previously included **in addition** to the custom login page. That registered a **second** `login` name pointing at Django’s built-in `LoginView`, which can confuse `reverse('login')` and redirects.

The project now uses **explicit** password-reset and password-change routes only (no `include('django.contrib.auth.urls')`). Your login page is always the custom `login_page` at `/` and `/login/`.

## Settings (already in `gate_analytics/settings.py`)

- `ALLOWED_HOSTS` includes `*` in `DEBUG` mode, or set `DJANGO_ALLOWED_HOSTS` in `.env`.
- `CSRF_TRUSTED_ORIGINS` includes ngrok subdomains; `NgrokCsrfTrustMiddleware` adds the current origin when the request comes from ngrok.
- `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` are set for HTTPS tunnels.

## Still stuck?

1. Open **DevTools → Network** → reload → select the **document** for `/` or `/login`.
2. Note **Status** (200, 302, 403, 502, etc.) and **Response** size.
3. Open **Console** for JavaScript errors.
4. On the server terminal, confirm a log line like: `"GET /login/ HTTP/1.1" 200 106575` (non‑zero size indicates HTML was sent).
