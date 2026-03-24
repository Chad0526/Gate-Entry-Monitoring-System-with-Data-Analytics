# Rename StaffGuardProfile → StaffPersonnelProfile and update User reverse relation
# name (related_name). Uses RenameModel so existing rows are preserved.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gate', '0070_rename_guard_field_verbose_names'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='StaffGuardProfile',
            new_name='StaffPersonnelProfile',
        ),
        migrations.AlterField(
            model_name='staffpersonnelprofile',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='staff_personnel_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
