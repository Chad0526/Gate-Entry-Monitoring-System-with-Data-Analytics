#!/usr/bin/env python
"""
Verification script for GuardNotification database setup.
Run this to verify notifications are properly stored in MySQL.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gate_analytics.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from gate.models import GuardNotification

def check_database_connection():
    """Check if database connection is working."""
    print("=" * 60)
    print("DATABASE CONNECTION CHECK")
    print("=" * 60)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"✓ Connected to database: {db_name}")
            print(f"✓ Database engine: {connection.settings_dict['ENGINE']}")
            print(f"✓ Database host: {connection.settings_dict['HOST']}")
            print(f"✓ Database port: {connection.settings_dict['PORT']}")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_table_exists():
    """Check if GuardNotification table exists."""
    print("\n" + "=" * 60)
    print("TABLE EXISTENCE CHECK")
    print("=" * 60)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'gate_guardnotification'
            """)
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                print("✓ Table 'gate_guardnotification' exists")
                
                # Get table structure
                cursor.execute("DESCRIBE gate_guardnotification")
                columns = cursor.fetchall()
                print(f"\n✓ Table has {len(columns)} columns:")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]})")
                
                return True
            else:
                print("✗ Table 'gate_guardnotification' does NOT exist")
                print("\nRun migrations to create the table:")
                print("  python manage.py migrate")
                return False
    except Exception as e:
        print(f"✗ Error checking table: {e}")
        return False

def check_notification_count():
    """Check how many notifications exist."""
    print("\n" + "=" * 60)
    print("NOTIFICATION COUNT CHECK")
    print("=" * 60)
    
    try:
        total = GuardNotification.objects.count()
        unread = GuardNotification.objects.filter(is_read=False).count()
        
        print(f"✓ Total notifications: {total}")
        print(f"✓ Unread notifications: {unread}")
        print(f"✓ Read notifications: {total - unread}")
        
        return True
    except Exception as e:
        print(f"✗ Error counting notifications: {e}")
        return False

def create_test_notification():
    """Create a test notification."""
    print("\n" + "=" * 60)
    print("TEST NOTIFICATION CREATION")
    print("=" * 60)
    
    try:
        # Find a guard user
        guards = User.objects.filter(groups__name='Guard')
        
        if not guards.exists():
            print("✗ No guard users found in the system")
            print("\nCreate a guard user first:")
            print("  1. Go to Django admin")
            print("  2. Create a user")
            print("  3. Add them to the 'Guard' group")
            return False
        
        guard = guards.first()
        print(f"✓ Found guard user: {guard.username}")
        
        # Create test notification
        notification = GuardNotification.objects.create(
            notification_type='system',
            priority='normal',
            title='Test Notification',
            message='This is a test notification to verify database storage.',
            target_guard=guard,
            broadcast=False
        )
        
        print(f"✓ Created test notification (ID: {notification.id})")
        print(f"  - Title: {notification.title}")
        print(f"  - Priority: {notification.priority}")
        print(f"  - Target: {notification.target_guard.username}")
        print(f"  - Created at: {notification.created_at}")
        
        # Verify it was saved to database
        saved = GuardNotification.objects.filter(id=notification.id).exists()
        if saved:
            print(f"✓ Notification successfully saved to MySQL database")
        else:
            print(f"✗ Notification NOT found in database")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error creating test notification: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification checks."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "GUARD NOTIFICATION DATABASE VERIFICATION" + " " * 7 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    checks = [
        ("Database Connection", check_database_connection),
        ("Table Existence", check_table_exists),
        ("Notification Count", check_notification_count),
        ("Test Notification", create_test_notification),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("\nNotifications are properly configured and stored in MySQL!")
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease fix the issues above and run this script again.")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
