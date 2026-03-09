# Switch to PostgreSQL for Production

## Why PostgreSQL?

- **SQLite** is fine for development and demos, but under **concurrent load** (e.g. 2+ guards scanning at once) it can lock the whole database and behave differently than in testing.
- **Panel defense line:** *"We tested concurrency in Postgres because SQLite locking differs."*
- For production and for capstone demos under load, use **PostgreSQL** (or MySQL).

---

## 1. Install PostgreSQL

### Windows
- Download from postgresql.org (Windows installer).
- Run installer; remember the postgres user password.

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

Open psql as postgres user, then:

```sql
CREATE DATABASE gate_analytics_db;
CREATE USER event_user WITH PASSWORD 'your_secure_password';
ALTER ROLE event_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE gate_analytics_db TO event_user;
\c gate_analytics_db
GRANT ALL ON SCHEMA public TO event_user;
```

---

## 3. Install Python driver

```bash
pip install psycopg2-binary
```

---

## 4. Configure Django

Use `.env` with production settings:

```ini
DB_NAME=gate_analytics_db
DB_USER=event_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

Run:

```bash
python manage.py migrate --settings=gate_analytics.settings_prod
python manage.py createsuperuser --settings=gate_analytics.settings_prod
```

---

## 5. Verify and screenshot for capstone

- Run load test: `python load_test_concurrent_scans.py` (expect 100/100 SUCCESS).
- Screenshot: `psql -U event_user -d gate_analytics_db -c "SELECT version();"`
- Screenshot: load test output.

This demonstrates production-ready database choice and concurrency testing.
