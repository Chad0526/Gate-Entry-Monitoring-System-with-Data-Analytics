# Backups and restore

Regular backups of the database and uploads (media) let you recover after failure or mistakes.

## Running a backup

From the project root (where `manage.py` is):

```bash
# Database only (SQLite copy or MySQL dump)
python manage.py backup_db

# Database + media (student photos, incidents, CKEditor uploads)
python manage.py backup_db --with-media

# Keep only the last 7 DB and 7 media backups (for scheduled runs)
python manage.py backup_db --with-media --retain 7
```

Output goes to the **`backups/`** folder:

- **SQLite:** `backups/db_YYYYMMDD_HHMMSS.sqlite3`
- **MySQL:** `backups/db_YYYYMMDD_HHMMSS.sql`
- **Media:** `backups/media_YYYYMMDD_HHMMSS.tar.gz`

**MySQL:** Ensure `mysqldump` is installed (MySQL client tools). Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` in `.env` if not using defaults.

---

## Scheduling automated backups

### Windows (Task Scheduler)

1. Open **Task Scheduler** → Create Basic Task.
2. Trigger: **Daily** (or Weekly) at a time when usage is low (e.g. 2:00 AM).
3. Action: **Start a program**
   - Program: `python` (or full path to your Python executable).
   - Arguments: `manage.py backup_db --with-media --retain 7`
   - Start in: your project folder (e.g. `C:\Users\RONNIE\PycharmProjects\django-event-management-master`).
4. Finish and test by right‑clicking the task → **Run**.

### Linux / macOS (cron)

```bash
# Edit crontab
crontab -e

# Example: every day at 2:00 AM, DB + media, keep last 7
0 2 * * * cd /path/to/django-event-management-master && python manage.py backup_db --with-media --retain 7
```

Use the real path to your project and the same `python` you use for the app (e.g. from a virtualenv).

---

## Restore (recover from backup)

**Important:** Stop the application (e.g. stop the Django server) before restoring so files and DB are not in use.

### SQLite

1. Copy the backup over the live database:
   ```bash
   copy backups\db_20260224_020000.sqlite3 db.sqlite3
   ```
   (or on Linux/macOS: `cp backups/db_20260224_020000.sqlite3 db.sqlite3`)
2. Restart the application.

### MySQL

1. Create a new database (or drop and recreate) if you want a clean restore:
   ```sql
   DROP DATABASE IF EXISTS gate_analytics_restore;
   CREATE DATABASE gate_analytics_restore CHARACTER SET utf8mb4;
   ```
2. Restore the dump:
   ```bash
   mysql -h 127.0.0.1 -u root -p gate_analytics_restore < backups/db_20260224_020000.sql
   ```
3. In `.env`, point `DB_NAME` to the restored database (`gate_analytics_restore`) or rename DBs as needed.
4. Restart the application.

### Media (uploads)

1. Unpack the tarball into a temporary folder, then copy contents into `media/`:
   ```bash
   tar -xzf backups/media_20260224_020000.tar.gz
   xcopy /E /Y media media   # Windows: copy extracted folder into project media
   ```
   On Linux/macOS:
   ```bash
   tar -xzf backups/media_20260224_020000.tar.gz
   cp -Rn media/* ./media/
   ```
2. Restart the application.

---

## Test restore (recommended)

Periodically test that backups are usable:

1. On a **test machine or copy of the project**, run a backup.
2. Restore the DB (and optionally media) as above into a **copy** of the app (e.g. different `DB_NAME` or a copy of `db.sqlite3`).
3. Start the app and log in, open dashboard, gate entries, and a few students/events to confirm data looks correct.

This confirms that scheduled backups will work when you need them.
