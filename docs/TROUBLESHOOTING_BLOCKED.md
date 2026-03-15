# Troubleshooting: "Blocked" when registering or logging in (SQLite / any database)

If you see **403 Access Denied** or **"Your IP address has been blocked"** when you:
- submit Staff/Faculty/Guard registration, or  
- try to log in (e.g. as staff1),

or if **login says "Account pending approval"**, use the steps below.

---

## 1. IP block (403 "Your IP has been blocked")

The app has **BlockedIPMiddleware**: any IP in the **Blocked IPs** list gets 403 on *all* requests (including login and registration). This is the same for SQLite, MySQL, or PostgreSQL.

**Fix:**

1. Open **Django Admin** from a different device/IP, or from the same machine after temporarily removing the block (see below).
2. Go to **Gate → Blocked IPs**.
3. Find your IP (or the one that was blocked):
   - Either **uncheck "Is active"** and save (unblocks but keeps the record), or  
   - **Delete** the record.
4. Reload the site; the block is cleared within about 30 seconds (middleware cache).

**If you can’t open admin** (same IP is blocked):

- **Option A – SQLite:** Close the app, then edit the SQLite DB and remove or deactivate the blocked IP:
  - Open `db.sqlite3` with a DB browser (e.g. DB Browser for SQLite).
  - Table: `gate_blockedip`.
  - Delete the row for your IP, or set `is_active` to `0`.
- **Option B – MySQL/PostgreSQL:** Use phpMyAdmin or psql and do the same (delete or set `is_active = false` in `gate_blockedip`).

---

## 2. Inactive account ("Account pending approval")

Staff/Faculty/Guard **self-registration** creates users with **is_active = False**. They cannot log in until an admin activates them.

**Fix:**

1. Log in to **Django Admin** as a superuser.
2. Go to **Auth → Users**.
3. Open the user (e.g. staff1 or the guard you registered).
4. **Check "Active"** (is_active).
5. Save.

After that, the user can log in. If the user has no role (Staff/Guard/Faculty group), add them to the correct group under **Auth → Users → [user] → Groups**.

---

## Summary

| Symptom | Cause | Fix |
|--------|--------|-----|
| 403 "Your IP has been blocked" | Your IP is in Blocked IPs | Admin → Gate → Blocked IPs → uncheck Is active or delete |
| "Account pending approval" on login | User created by registration has is_active=False | Admin → Auth → Users → [user] → check Active |
| "Your account has no role" | User has no Staff/Guard/Faculty/Admin group | Admin → Auth → Users → [user] → add to correct Group |

SQLite does not change this behavior; blocking and inactive accounts work the same with any database.
