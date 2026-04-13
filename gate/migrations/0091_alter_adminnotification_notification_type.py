# Generated manually for new AdminNotification types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0090_sittheme_signatory_signatures'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminnotification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('student_registration', 'Student Registration'),
                    ('staff_personnel_registration', 'Staff/Faculty/Personnel Registration'),
                    ('incident', 'Incident Alert'),
                    ('sas_inactive_ready_activation', 'SAS checked — inactive student ready to activate'),
                    ('sas_verified_gate_followup', 'SAS verified gate incident — student cleared'),
                    ('gate_manual_referral', 'Guard manual entry — office referral'),
                    ('capacity', 'Capacity Alert'),
                    ('system', 'System Message'),
                    ('personnel_alert', 'Personnel alert'),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
    ]
