# Switching databases (SQLite / MySQL / PostgreSQL)

You **do not need a separate virtual environment** for each database. Use **one venv** and switch databases by changing your `.env` file.

## Options

| Database   | When to use                          | `.env` setting      |
|-----------|--------------------------------------|---------------------|
| **SQLite**   | Quick local dev, no server, few bugs  | `DB_ENGINE=sqlite` (or leave unset) |
| **MySQL**    | XAMPP / MariaDB, shared hosting       | `DB_ENGINE=mysql` + MySQL vars below |
| **PostgreSQL** | Production, timezone-safe reporting  | `DB_ENGINE=postgresql` + PostgreSQL vars |

Same codebase, same venv — only `.env` and the running database server change.

---

## 1. Use SQLite (no server)

- No DB server needed.
- Good when PostgreSQL or MySQL have issues, or for quick local testing.

**.env:**
```env
DB_ENGINE=sqlite
```
(Or remove/comment out `DB_ENGINE`; SQLite is the default.)

Then:
```bash
python manage.py migrate
python manage.py runserver
```

---

## 2. Use MySQL (e.g. XAMPP)

1. **Start MySQL** in XAMPP (Apache optional).

2. **Create a database** (e.g. in phpMyAdmin):
   - Open http://localhost/phpmyadmin
   - Create database: `gate_analytics` (or another name)
   - Collation: `utf8mb4_unicode_ci`

3. **Install driver** (once, in your existing venv):
   ```bash
   pip install mysqlclient
   ```
   (Already in `requirements.txt`; if you did `pip install -r requirements.txt`, you have it.)

4. **Point Django to MySQL** in `.env`:
   ```env
   DB_ENGINE=mysql
   DB_NAME=gate_analytics
   DB_USER=root
   DB_PASSWORD=
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```
   Use your XAMPP MySQL user/password. Use `127.0.0.1`, not `localhost`, on Windows.

5. **Run migrations:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## 3. Use PostgreSQL

**.env:** set `DB_ENGINE=postgresql` and the PostgreSQL vars (name, user, password, host, port). Then:

```bash
pip install psycopg2-binary   # if not already installed
python manage.py migrate
python manage.py runserver
```

---

## When something breaks on one database

- **PostgreSQL issues** → switch `.env` to `DB_ENGINE=sqlite` or `DB_ENGINE=mysql` (with MySQL running), run `migrate`, and test.
- **MySQL issues** → switch to `DB_ENGINE=sqlite` or `DB_ENGINE=postgresql` and run `migrate`.
- **Quick local test** → use `DB_ENGINE=sqlite`; no server needed.

You only need **one virtual environment**; install all drivers once:

```bash
pip install -r requirements.txt
```

That gives you SQLite (built-in), `mysqlclient` (MySQL), and `psycopg2-binary` (PostgreSQL). Switch databases by editing `.env` and running `migrate` when you change `DB_ENGINE`.

---

## Compatibility (MySQL and PostgreSQL)

All app features (login, registration, staff/guard approval, notifications, reports) are written to work on **MySQL** and **PostgreSQL**. Queries use the Django ORM only; no database-specific SQL is used for these flows. SQLite is also supported for local development.
