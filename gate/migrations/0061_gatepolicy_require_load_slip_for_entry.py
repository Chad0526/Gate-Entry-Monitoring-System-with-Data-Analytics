# Migration: require load slip for entry (gate strictly based on load slip)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0060_staffguardprofile_preferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='gatepolicy',
            name='require_load_slip_for_entry',
            field=models.BooleanField(default=False, help_text='If True, deny entry when student has no load slip; contact registrar.'),
        ),
    ]
