# Generated migration for StaffGuardProfile preferences (language, timezone, email notifications)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0059_backfill_staff_guard_profile_complete'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffguardprofile',
            name='preferred_language',
            field=models.CharField(blank=True, default='en', max_length=10),
        ),
        migrations.AddField(
            model_name='staffguardprofile',
            name='preferred_timezone',
            field=models.CharField(blank=True, default='Asia/Manila', max_length=63),
        ),
        migrations.AddField(
            model_name='staffguardprofile',
            name='email_notifications_announcements',
            field=models.BooleanField(
                default=True,
                help_text='Receive email notifications for announcements.',
            ),
        ),
    ]
