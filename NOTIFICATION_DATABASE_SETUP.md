# Guard Notification Database Setup - MySQL

## Current Status

The `GuardNotification` model is **already defined** and **migrations exist**. The system is configured to use MySQL when `DB_ENGINE=mysql` is set in your `.env` file.

## Database Configuration

Your `.env` file should have:

```env
DB_ENGINE=mysql
DB_NAME=gate_analytics
DB_USER=root
DB_PASSWORD=your_password_here
DB_HOST=127.0.0.1
DB_PORT=3306
```

## Verification Steps

### Step 1: Check Database Connection

```bash
python manage.py dbshell
```

If this opens MySQL shell, your connection is working. Type `exit` to quit.

### Step 2: Verify Table Exists

Run the verification script:

```bash
python verify_notifications_db.py
```

This will check:
- ✓ Database connection
- ✓ Table existence
- ✓ Notification count
- ✓ Create test notification

### Step 3: Run Migrations (if needed)

If the table doesn't exist, run:

```bash
python manage.py migrate gate
```

This will create the `gate_guardnotification` table in MySQL.

### Step 4: Verify in MySQL Directly

```bash
mysql -u root -p
```

Then run:

```sql
USE gate_analytics;

-- Show table structure
DESCRIBE gate_guardnotification;

-- Count notifications
SELECT COUNT(*) FROM gate_guardnotification;

-- Show recent notifications
SELECT id, title, priority, target_guard_id, is_read, created_at 
FROM gate_guardnotification 
ORDER BY created_at DESC 
LIMIT 5;
```

## GuardNotification Table Structure

The table has these columns:

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| notification_type | VARCHAR(20) | Type: incident, capacity, shift_reminder, suspicious, system |
| priority | VARCHAR(10) | Priority: low, medium, high, urgent |
| title | VARCHAR(200) | Notification title |
| message | TEXT | Notification message (max 1000 chars) |
| target_guard_id | INT | Foreign key to auth_user (guard) |
| broadcast | BOOLEAN | True if sent to all guards |
| related_incident_id | INT | Optional link to incident |
| related_event_id | INT | Optional link to event |
| related_entry_id | INT | Optional link to gate entry |
| is_read | BOOLEAN | Read status |
| read_at | DATETIME | When notification was read |
| created_at | DATETIME | When notification was created |
| expires_at | DATETIME | Optional expiration time |

## Creating Test Notifications

### Method 1: Using Django Admin

1. Go to http://127.0.0.1:8000/admin/
2. Navigate to "Gate" → "Guard notifications"
3. Click "Add guard notification"
4. Fill in the form and save

### Method 2: Using Admin Notification Sender

1. Login as admin/supervisor
2. Go to "Guard Activity" page
3. Use the "Send Notification to Guards" form
4. Select recipient, priority, and message
5. Click "Send Notification"

### Method 3: Using Django Shell

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from gate.models import GuardNotification

# Find a guard
guard = User.objects.filter(groups__name='Guard').first()

# Create notification
notification = GuardNotification.objects.create(
    notification_type='system',
    priority='high',
    title='Test Alert',
    message='This is a test notification',
    target_guard=guard,
    broadcast=False
)

print(f"Created notification ID: {notification.id}")
```

### Method 4: Using Verification Script

```bash
python verify_notifications_db.py
```

This automatically creates a test notification.

## Troubleshooting

### Issue: Table doesn't exist

**Solution:**
```bash
python manage.py migrate gate
```

### Issue: Migration already applied but table missing

**Solution:**
```bash
# Check migration status
python manage.py showmigrations gate

# If 0049_auto_20260305_1526 is checked but table missing, fake rollback and re-apply
python manage.py migrate gate 0048 --fake
python manage.py migrate gate
```

### Issue: MySQL connection error

**Solution:**
1. Verify MySQL is running (XAMPP/WAMP)
2. Check `.env` file has correct credentials
3. Test connection: `mysql -u root -p`
4. Verify database exists: `SHOW DATABASES;`

### Issue: Character encoding errors

**Solution:**
The settings already include `'charset': 'utf8mb4'` which supports all characters including emojis.

## Verification Checklist

- [ ] MySQL is running
- [ ] `.env` has `DB_ENGINE=mysql`
- [ ] Database `gate_analytics` exists
- [ ] Migrations are applied
- [ ] Table `gate_guardnotification` exists
- [ ] Can create test notification
- [ ] Notification appears in database
- [ ] Notification appears in guard dashboard
- [ ] Sound plays when notification arrives
- [ ] Clicking notification navigates to notifications page

## Next Steps

After verifying the database setup:

1. **Test the notification system:**
   - Login as admin
   - Send a test notification to a guard
   - Login as that guard
   - Check if notification appears in dashboard
   - Check if sound plays
   - Click notification to navigate

2. **Monitor the database:**
   ```sql
   -- Watch for new notifications
   SELECT * FROM gate_guardnotification ORDER BY created_at DESC LIMIT 10;
   ```

3. **Check logs:**
   - Open browser console (F12)
   - Look for notification polling logs
   - Verify API calls are successful

## Support

If you encounter issues:

1. Run the verification script: `python verify_notifications_db.py`
2. Check browser console for JavaScript errors
3. Check Django logs for backend errors
4. Verify MySQL table exists and has correct structure
5. Test with a simple notification first before complex scenarios
