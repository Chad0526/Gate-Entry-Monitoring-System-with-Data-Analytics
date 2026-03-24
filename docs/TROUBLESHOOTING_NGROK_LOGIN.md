# Step-by-step: login page not showing (LAN / ngrok)

## Read first: ngrok **Free** plan

On the **free** tier, ngrok injects an **interstitial warning page** before your app (not Django). It can look **blank** if extensions block scripts/cookies. See **[NGROK_FREE_TIER_INTERSTITIAL.md](NGROK_FREE_TIER_INTERSTITIAL.md)** and open **`/ngrok-help/`** on your server for the official bypass options (Visit button, header, User-Agent, or paid plan).

---

Do these **in order**. Stop when something fails—that step is where the problem is.

---

### Step 1 — Django on this PC only

1. Start the server: `python manage.py runserver` (or `runserver_global.bat` for all interfaces).
2. In a browser on **the same machine**, open: **http://127.0.0.1:8000/login/**

**Expected:** Full login page (forms, green styling).

- **If this fails:** Fix database, migrations, or runserver errors in the terminal first—not ngrok.

---

### Step 2 — Plain “health” (no HTML templates)

In the browser: **http://127.0.0.1:8000/ping/**

**Expected:** The single word `ok` (plain text).

- **If not `ok`:** Database connection may be failing (`health_check` checks DB).

---

### Step 3 — Minimal HTML (no big login template)

Open: **http://127.0.0.1:8000/login-probe/**

**Expected:** A small page titled “Django is responding” with links.

- **If Step 1 works but this fails:** Unlikely; report the error.
- **If Step 2 works but Step 1 fails:** Suspect template/static issue on the full login page.

---

### Step 4 — Listen on all interfaces (phone / another PC on Wi‑Fi)

Run: `python manage.py runserver 0.0.0.0:8000` (or `runserver_global.bat`).

On **another device** on the same Wi‑Fi, open: **http://&lt;THIS-PC-LAN-IP&gt;:8000/login-probe/**  
(Find the IP with `ipconfig` on Windows.)

**Expected:** Same probe page.

- **If it fails:** **Windows Firewall** may be blocking Python—allow it on **Private** networks, or add an inbound rule for TCP port 8000.

---

### Step 5 — ngrok tunnel

1. Install/start [ngrok](https://ngrok.com/) on **the same PC** that runs Django.
2. Run: `ngrok http 8000` (same port as `runserver`).
3. Copy the **https** URL ngrok prints.

**Expected:** ngrok dashboard shows requests when you load pages.

---

### Step 6 — ngrok “browser warning” (free tier)

Free ngrok often shows an **interstitial** page (“You are about to visit…”) with a **Visit Site** button.

1. Open the ngrok **https** URL in the browser.
2. If you see that warning, click **Visit Site** (or equivalent).
3. Then try: **https://&lt;your-subdomain&gt;.ngrok-free.dev/login-probe/**

**Expected:** The same minimal probe page as Step 3.

- **If the tab stays blank:** Try **another browser** or **InPrivate/Incognito**, disable **ad blockers**, and check **DevTools → Network** for failed requests (red lines).

---

### Step 7 — Compare probe vs full login

| URL | Purpose |
|-----|--------|
| `/ping/` | Plain `ok` — tunnel + Django + DB |
| `/login-probe/` | Tiny HTML — routing + `ALLOWED_HOSTS` |
| `/login/` | Full app login — templates + static files |

If **probe works** but **`/login/` is blank**, open **DevTools → Console** on `/login/` and note JavaScript errors; check **Network** for CSS/JS **404** or blocked requests.

---

### Settings checklist (already in project)

- With **`DEBUG=True`**, **`ALLOWED_HOSTS`** defaults to **`['*']`** unless **`DJANGO_ALLOWED_HOSTS`** is set in `.env`.
- **`CSRF_TRUSTED_ORIGINS`** includes ngrok-style hosts; **`NgrokCsrfTrustMiddleware`** can add the current Origin dynamically.

---

### Still stuck?

Note down:

1. Result of **Step 1** (yes/no).
2. Result of **`/ping/`** (`ok` or not).
3. Result of **`/login-probe/`** through ngrok (yes/no).
4. **Screenshot** of **Network** (first document row) and **Console** for `/login/`.

That isolates tunnel vs Django vs template vs browser.
