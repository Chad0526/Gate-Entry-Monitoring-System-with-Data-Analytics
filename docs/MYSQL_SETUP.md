# Using MySQL as the Database

This project supports MySQL. To switch from SQLite (or another backend) to MySQL, follow these steps.

## Prerequisites

- **MySQL server** (5.7+ or 8.x) installed and running.
- **mysqlclient** Python package (already in `requirements.txt`). Install with:
  ```bash
  pip install mysqlclient
  ```
  On Windows, if installation fails, use a wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient) or install MySQL Connector/C first.

## 1. Create the MySQL database

In MySQL (command line or MySQL Workbench), create a database and optionally a dedicated user:

```sql
CREATE DATABASE gate_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Optional: create a user (replace YOUR_PASSWORD with a strong password)
CREATE USER 'gate_user'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON gate_analytics.* TO 'gate_user'@'localhost';
FLUSH PRIVILEGES;
```

If you use the default `root` user, you can skip the `CREATE USER` / `GRANT` part and use `root` in `.env` below.

## 2. Configure environment variables

Copy `.env.example` to `.env` (if you don’t have `.env` yet), then set:

```env
DB_ENGINE=mysql
DB_NAME=gate_analytics
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

- Use the database name you created in step 1.
- Use the user and password that have access to that database.
- If MySQL is on another machine, set `DB_HOST` to that host (e.g. `192.168.1.10`).

## 3. Run migrations on MySQL

With `DB_ENGINE=mysql` and the correct credentials in `.env`, run:

```bash
python manage.py migrate
```

This creates all tables in MySQL. The app is now using MySQL.

## 4. Create a superuser (if starting fresh)

```bash
python manage.py createsuperuser
```

## 5. (Optional) Migrate existing data from SQLite to MySQL

If you were using SQLite and want to move your data to MySQL:

1. **While still using SQLite** (do not set `DB_ENGINE=mysql` yet), export data:
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -o backups/sqlite_data.json
   ```
   Excluding `contenttypes` and `auth.Permission` avoids conflicts when loading into a fresh MySQL database.

2. **Switch to MySQL**: set `DB_ENGINE=mysql` and MySQL credentials in `.env`.

3. **Apply schema on MySQL** (if not already done):
   ```bash
   python manage.py migrate
   ```

4. **Load the data**:
   ```bash
   python manage.py loaddata backups/sqlite_data.json
   ```

5. If you see errors about duplicate or invalid keys, you may need to export/import only specific app labels (e.g. `gate`, `auth`) and fix conflicts manually. For a clean start, you can skip loaddata and re-import students (e.g. CSV) and re-create other data.

## 6. Register sample students (if needed)

After using MySQL, you can seed the 50 sample students for load slip import:

```bash
python manage.py register_sample_csv_students
```

## 7. Run the application

```bash
python manage.py runserver
```

The app will use MySQL for all database access. Backup can be done with `python manage.py backup_db` (see below for MySQL backup support).

## Troubleshooting

- **“Access denied”**: Check `DB_USER`, `DB_PASSWORD`, and that the user has privileges on `DB_NAME`.
- **“Unknown database”**: Run the `CREATE DATABASE` command from step 1.
- **“Can’t connect to MySQL server”**: Ensure MySQL is running and `DB_HOST` / `DB_PORT` are correct (e.g. use `127.0.0.1` and `3306` for local).
- **charset/collation**: The project sets `charset=utf8mb4` in Django’s MySQL options; the database created with `utf8mb4_unicode_ci` is compatible.
