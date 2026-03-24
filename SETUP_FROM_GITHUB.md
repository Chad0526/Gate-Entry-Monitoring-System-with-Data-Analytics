# Setup: Run the project from GitHub

Use these steps when you clone the repo (on a new PC, or after a fresh clone).

---

## 1. Clone the repository

```bash
git clone https://github.com/Chad0526/Gate-Entry-Monitoring-System-with-Data-Analytics.git
cd Gate-Entry-Monitoring-System-with-Data-Analytics
```

*(If you already have the folder, skip to step 2.)*

---

## 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv env
.\env\Scripts\activate.bat
```

**Linux / macOS:**
```bash
python3 -m venv env
source env/bin/activate
```

You should see `(env)` in your prompt.

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Environment variables (.env)

The `.env` file is **not** in the repo (for security). Create it from the example:

1. Copy the example file:
   - **Windows:** `copy .env.example .env`
   - **Linux/macOS:** `cp .env.example .env`

2. Edit `.env` and set at least:
   - `DJANGO_SECRET_KEY` – use a long random string (e.g. generate one at [djecrety.ir](https://djecrety.ir/))
   - `ALLOWED_HOSTS` – e.g. `localhost,127.0.0.1` for local use

3. **Database (choose one):**
   - **SQLite (easiest):** Leave `DB_ENGINE` commented out or set `DB_ENGINE=sqlite`. No other DB_* needed.
   - **MySQL:** Set `DB_ENGINE=mysql` and fill `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
   - **PostgreSQL:** Set `DB_ENGINE=postgresql` and fill the PostgreSQL variables.

4. **Optional:** Email (EMAIL_HOST, EMAIL_HOST_USER, etc.) if you use email features.

---

## 5. Database migrations

```bash
python manage.py migrate
```

---

## 6. Create an admin user (first time only)

```bash
python manage.py createsuperuser
```

Enter username, email, and password when prompted.

---

## 7. (Optional) Filipino locale

If you use Filipino language on the dashboard, compile the locale (generates the `.mo` file):

```bash
python compile_fil_locale.py
```

---

## 8. Collect static files (recommended before production)

Django copies CSS, JS, and CKEditor into `staticfiles/` when you run:

```bash
python manage.py collectstatic --noinput
```

Skip for quick local dev if `DEBUG=True` serves `static/`; **required** for production or if admin/CKEditor assets are missing.

---

## 9. Run the server

```bash
python manage.py runserver 8001
```

*(Or use `runserver` without a number for port 8000.)*

- Open in browser: **http://127.0.0.1:8001/** (or 8000).
- Log in with the superuser account (or any user you created).

---

## Quick checklist

| Step | Command / action |
|------|-------------------|
| 1 | `git clone ...` and `cd` into the folder |
| 2 | `python -m venv env` then activate it |
| 3 | `pip install -r requirements.txt` |
| 4 | Copy `.env.example` to `.env` and edit it |
| 5 | `python manage.py migrate` |
| 6 | `python manage.py createsuperuser` (first time) |
| 7 | `python compile_fil_locale.py` (optional, for Filipino) |
| 8 | `python manage.py collectstatic --noinput` (optional local; required for prod) |
| 9 | `python manage.py runserver 8001` |

---

## If you already have the project (same PC)

- Open the project folder, activate the venv (`.\env\Scripts\Activate.ps1` or `source env/bin/activate`).
- If you pulled new code: `pip install -r requirements.txt`, `python manage.py migrate`, then `python compile_fil_locale.py` if you use Filipino.
- Run: `python manage.py runserver 8001`.
