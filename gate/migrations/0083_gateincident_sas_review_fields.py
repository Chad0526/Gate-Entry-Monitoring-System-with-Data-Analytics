from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0082_remove_student_rejection_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='gateincident',
            name='sas_check_notes',
            field=models.CharField(blank=True, default='', help_text='Optional Student Affairs review note.', max_length=255),
        ),
        migrations.AddField(
            model_name='gateincident',
            name='sas_checked_at',
            field=models.DateTimeField(blank=True, help_text='When Student Affairs marked this incident as verified.', null=True),
        ),
        migrations.AddField(
            model_name='gateincident',
            name='sas_checked_by',
            field=models.ForeignKey(blank=True, help_text='Student Affairs/admin user who verified this incident.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gate_incidents_checked', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='gateincident',
            name='sas_review_status',
            field=models.CharField(choices=[('to_check', 'To be checked'), ('verified', 'Verified by Student Affairs')], db_index=True, default='to_check', help_text='Student Affairs review status for ID mismatch follow-up.', max_length=20),
        ),
    ]
