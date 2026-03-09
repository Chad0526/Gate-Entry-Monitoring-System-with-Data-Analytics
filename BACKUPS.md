# Scheduled backups

Regular backups help you recover from failures or mistakes. Use the management command and schedule it with cron (Linux/macOS) or Task Scheduler (Windows).

## Commands

- **Database only**  
  `python manage.py backup_db`  
  Writes to `backups/db_YYYYMMDD_HHMMSS.sqlite3` (SQLite) or `.sql` (MySQL/PostgreSQL).

- **Database + media (uploads)**  
  `python manage.py backup_db --with-media`  
  Same as above, plus `backups/media_YYYYMMDD_HHMMSS.tar.gz` containing `MEDIA_ROOT`.

- **Custom output path**  
  `python manage.py backup_db --output /path/to/backup.sql`  
  `python manage.py backup_db --with-media --output /path/to/db.sql`

## Scheduling (cron example)

From the project root (where `manage.py` lives):

```bash
# Every day at 2:00 AM: DB + media
0 2 * * * cd /path/to/django-event-management-master && python manage.py backup_db --with-media

# Every 6 hours: DB only
0 */6 * * * cd /path/to/django-event-management-master && python manage.py backup_db
```

Use the correct path and Python (or virtualenv) in the cron job.

## Restore

- **SQLite:** stop the app, replace `db.sqlite3` with the backup file, restart.
- **MySQL:** `mysql -u USER -p DB_NAME < backups/db_YYYYMMDD_HHMMSS.sql`
- **PostgreSQL:** `psql -U USER DB_NAME < backups/db_YYYYMMDD_HHMMSS.sql`
- **Media:** extract the tarball over `MEDIA_ROOT` (or into a new folder and point `MEDIA_ROOT` there).

Test a restore on a copy of the database so you know the process works.
