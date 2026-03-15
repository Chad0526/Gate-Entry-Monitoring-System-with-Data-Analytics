# Switch to PostgreSQL

## Why PostgreSQL?

- **SQLite** is fine for development and demos, but under **concurrent load** (e.g. 2+ guards scanning at once) it can lock the whole database and behave differently than in testing.
- **Panel defense line:** *"We tested concurrency in Postgres because SQLite locking differs."*
- For production and for capstone demos under load, use **PostgreSQL** (or MySQL).

This project is fully supported on PostgreSQL: migrations, backups (`backup_db`), connection check (`check_db`), and middleware are all compatible. The only requirement is that the connection uses UTC (configured in `settings.py`).

---

## 1. Install PostgreSQL

### Windows
- Download from [postgresql.org](https://www.postgresql.org/download/windows/) (Windows installer).
- Run installer; remember the **postgres** user password you set.
- Optional: add PostgreSQL **bin** to PATH (e.g. `C:\Program Files\PostgreSQL\16\bin`) so you can run `psql` from any terminal.

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

---

## 2. Create database and user

Open **psql** (as postgres user, or via pgAdmin / SQL Shell):

**Windows:** Open "SQL Shell (psql)" from Start Menu, press Enter for defaults, enter postgres password when asked.

**Linux/macOS:** `sudo -u postgres psql` or `psql -U postgres`

Then run:

```sql
CREATE DATABASE gate_analytics_db;
CREATE USER event_user WITH PASSWORD 'your_secure_password';
ALTER ROLE event_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE gate_analytics_db TO event_user;
\c gate_analytics_db
GRANT ALL ON SCHEMA public TO event_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO event_user;
\q
```

Use a strong password and replace `event_user` / `gate_analytics_db` if you prefer different names (then use the same in `.env` below).

---

## 3. Install Python driver

```bash
pip install psycopg2-binary
```

(Already in `requirements.txt`; if you use `pip install -r requirements.txt` you’re set.)

---

## 4. Configure Django with .env

In your project root, edit **`.env`** (or create from `.env.example`). Set:

```ini
DB_ENGINE=postgresql
DB_NAME=gate_analytics_db
DB_USER=event_user
DB_PASSWORD=your_secure_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

- Use the database name and user you created in step 2.
- On Windows, use `127.0.0.1` instead of `localhost` to avoid IPv6 issues.
- If PostgreSQL is on a non-default port (e.g. 3307), set `DB_PORT=3307` in `.env`.

**Important:** The project sets the connection timezone to UTC in `settings.py` (`options: '-c timezone=UTC'`). This is required when `USE_TZ = True` so Django’s timezone-aware datetimes work correctly. Do not remove it.

---

## 5. Migrate and create superuser

From the project root:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Then run the app:

```bash
python manage.py runserver
```

Django now uses PostgreSQL. No separate settings file is required; the main `settings.py` reads `DB_ENGINE=postgresql` from `.env`.

---

## 6. Verify connection and backups

**Test the connection:**
```bash
python manage.py check_db
```
This confirms Django can connect to PostgreSQL (and works for SQLite/MySQL too).

**Back up the database:**
```bash
python manage.py backup_db
```
With PostgreSQL, this runs `pg_dump` and writes a `.sql` file under `backups/`. Use `backup_db --with-media` to include media files, and `--retain N` to keep only the last N backups when scheduling.

---

## 7. (Optional) Verify and screenshot for capstone

- Run load test (if you have it): `python load_test_concurrent_scans.py` (expect 100/100 SUCCESS).
- Screenshot: `psql -U event_user -d gate_analytics_db -c "SELECT version();"`
- Screenshot: load test output.

This demonstrates production-ready database choice and concurrency testing.
