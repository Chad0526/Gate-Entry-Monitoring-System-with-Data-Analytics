# ngrok tunnel checklist (localhost works, public URL does not)

If **`http://127.0.0.1:8000/`** works but **`https://xxxx.ngrok-free.dev/`** does not, walk through these in order.

---

## ERR_NGROK_8012 — “Bad Gateway” / upstream connection failed

You see HTML from **ngrok** (not Django) saying traffic reached the ngrok agent but **failed to connect to `localhost:8000`**, or `dial tcp [::1]:8000: … connection refused`.

| Cause | Fix |
|--------|-----|
| **Django is not running** | Start it **before** ngrok: `python manage.py runserver 127.0.0.1:8000` or `runserver_global.bat`. |
| **Wrong port** | ngrok must use the **same** port as `runserver` (e.g. both **8000**). |
| **Windows: `localhost` = IPv6 `[::1]`** but Django only on **IPv4** | Use **`ngrok http 127.0.0.1:8000`** instead of `ngrok http 8000` so the upstream is explicit IPv4. |

After fixing, **`http://127.0.0.1:8000/ping/`** must return **`ok`** locally; then the public URL will work.

---

## 1. Same port everywhere

Django and ngrok must use the **same port number**.

| What | Example |
|------|--------|
| Terminal running Django | `Starting development server at http://127.0.0.1:8000/` |
| ngrok command | `ngrok http 8000` (not 8080, not 8001) |

If you use another port (e.g. PyCharm uses 8001), run:

`ngrok http 8001`

---

## 2. Bind Django to IPv4 explicitly (optional but fixes some Windows setups)

Start Django with:

```text
python manage.py runserver 127.0.0.1:8000
```

Start ngrok with an explicit upstream:

```text
ngrok http 127.0.0.1:8000
```

This avoids rare **IPv6 `localhost`** vs **`127.0.0.1`** mismatches.

---

## 3. ngrok agent is logged in

One-time:

```text
ngrok config add-authtoken YOUR_TOKEN
```

(Get the token from [ngrok dashboard](https://dashboard.ngrok.com/).)  
Without a valid token, tunnels may not start or may fail silently.

---

## 4. Prove the tunnel reaches Django (bypasses the browser)

From **PowerShell** on the **same PC** that runs Django + ngrok, run (replace with your URL):

```powershell
curl.exe -sS -H "ngrok-skip-browser-warning: 1" "https://YOUR-SUBDOMAIN.ngrok-free.dev/ping/"
```

**Expected:** the single word `ok`.

| Result | Meaning |
|--------|--------|
| `ok` | **Tunnel is fine.** Django is receiving traffic. If the normal browser still looks blank, it is almost always the **ngrok free interstitial** or extensions—see [NGROK_FREE_TIER_INTERSTITIAL.md](NGROK_FREE_TIER_INTERSTITIAL.md). |
| Connection refused / failed to connect | ngrok is not running, wrong URL, or tunnel points to wrong port. |
| `502` / `503` from ngrok | Nothing listening on the address/port ngrok forwards to—start Django first. |
| `400` / DisallowedHost | Set `DEBUG=True` or `DJANGO_ALLOWED_HOSTS=*` in dev (see `settings.py`). |

Or use the helper (from the **project root** folder):

```bat
verify-ngrok-tunnel.bat https://YOUR-SUBDOMAIN.ngrok-free.dev
```

PowerShell (note the **`.\`** — required for scripts in the current directory):

```powershell
.\scripts\verify-ngrok-tunnel.ps1 -Url "https://YOUR-SUBDOMAIN.ngrok-free.dev"
```

---

## 5. ngrok “Forwarding” line must match your Django port

When ngrok starts, you should see something like:

```text
Forwarding   https://abc123.ngrok-free.dev -> http://localhost:8000
```

The **right-hand** side must be the host/port where **runserver** is listening.

---

## 6. Browser vs tunnel

- **Tunnel broken:** `curl` with the header (step 4) fails.
- **Tunnel OK, browser blank:** ngrok free **warning page** or blocked scripts—see [NGROK_FREE_TIER_INTERSTITIAL.md](NGROK_FREE_TIER_INTERSTITIAL.md).

---

## 7. This project’s Django settings (already OK for tunnels)

With **`DEBUG=True`** and no restrictive `DJANGO_ALLOWED_HOSTS`, **`ALLOWED_HOSTS`** includes `*`.  
**`SECURE_PROXY_SSL_HEADER`** and **`USE_X_FORWARDED_HOST`** are set so HTTPS via ngrok is handled correctly.

No extra Django change is required for tunneling **if** the port matches and ngrok is authenticated.
