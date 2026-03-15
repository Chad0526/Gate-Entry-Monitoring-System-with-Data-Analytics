# Data migration: mark existing staff/guard profiles as complete so current users are not forced to the form

from django.db import migrations


def backfill_profile_complete(apps, schema_editor):
    StaffGuardProfile = apps.get_model('gate', 'StaffGuardProfile')
    # Mark all existing staff/guard profiles as complete so current users keep full access.
    # Only new registrations (created with profile_complete=False) will see the complete-profile form.
    StaffGuardProfile.objects.filter(profile_complete=False).update(profile_complete=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0058_staffguardprofile_profile_complete'),
    ]

    operations = [
        migrations.RunPython(backfill_profile_complete, noop),
    ]
