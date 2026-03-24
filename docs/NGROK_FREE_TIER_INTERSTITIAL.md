# ngrok Free: why the page looks blank (deep check)

This is **not a bug in your Django project**. ngrok’s **free developer plan** inserts an **[interstitial warning page](https://ngrok.com/docs/pricing-limits/free-plan-limits/#removing-the-interstitial-page)** in front of **HTML** traffic in normal browsers. It exists to reduce phishing abuse.

## What you see

- A full-screen or minimal ngrok page asking the visitor to confirm before continuing.
- Sometimes it **looks like a white/blank tab** if:
  - JavaScript is blocked,
  - privacy extensions interfere,
  - cookies are blocked (ngrok sets a cookie after you click **Visit** so the warning may not show again for ~7 days for that domain),
  - or the browser fails to render the interstitial.

Your app only runs **after** ngrok forwards the request to `localhost`. Until then, **Django is never involved**.

## Confirm Django is fine (same PC)

Always test without ngrok first:

| URL | Expected |
|-----|----------|
| `http://127.0.0.1:8000/ping/` | Plain text `ok` |
| `http://127.0.0.1:8000/login-probe/` | Small HTML page |
| `http://127.0.0.1:8000/login/` | Full login UI |

If these work, **your system is OK**; the tunnel layer is the variable.

## Official ways to deal with the free-tier interstitial

From [ngrok’s documentation](https://ngrok.com/docs/pricing-limits/free-plan-limits/#removing-the-interstitial-page):

1. **Click through**  
   Use the **Visit** / continue button on the interstitial. After that, ngrok sets a cookie so you may not see it again for that domain for several days.

2. **Request header (API / tools)**  
   Add header: `ngrok-skip-browser-warning: 1` (value can be any).  
   Example: `curl -H "ngrok-skip-browser-warning: 1" https://YOUR-URL.ngrok-free.dev/ping/`

3. **Browser extension (development)**  
   Add the same header for `*.ngrok-free.dev` / `*.ngrok-free.app` (e.g. **ModHeader**, **Requestly**).  
   ngrok **does not** allow adding this header via their Traffic Policy on free accounts to bypass the warning.

4. **Non-standard User-Agent**  
   ngrok documents that a **custom User-Agent** (e.g. `MyApp/0.0.1`) can bypass the interstitial for browser-like requests. Use a UA switcher extension **only for development** on ngrok URLs.

5. **Paid ngrok plan**  
   Removes the interstitial for normal browsing.

## Tunnel checklist (still required)

- `python manage.py runserver` (or `0.0.0.0:8000`) is **running**.
- `ngrok http <SAME_PORT>` (e.g. both **8000**).
- ngrok shows **Forwarding** `https://…` → `http://localhost:8000`.
- You use the **https** URL ngrok prints.

## In-app help page

After you can load any page through the tunnel, open:

**`/ngrok-help/`**

for a short summary and links to `/ping/`, `/login-probe/`, and `/login/`.

---

**Reference:** [Removing the interstitial page (ngrok docs)](https://ngrok.com/docs/pricing-limits/free-plan-limits/#removing-the-interstitial-page)
