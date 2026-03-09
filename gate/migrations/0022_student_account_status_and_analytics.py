# Generated manually for Student account status and analytics fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_initial_account_status(apps, schema_editor):
    Student = apps.get_model('gate', 'Student')
    Student.objects.filter(is_active=True).update(account_status='APPROVED')
    Student.objects.filter(is_active=False).update(account_status='PENDING')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gate', '0021_add_visitor_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='account_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('INACTIVE', 'Inactive')],
                db_index=True,
                default='PENDING',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='student',
            name='approved_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students_approved',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='student',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='student',
            name='course',
            field=models.CharField(blank=True, choices=[('BSIT', 'BSIT'), ('BSED', 'BSED'), ('BEED', 'BEED')], max_length=20),
        ),
        migrations.AddField(
            model_name='student',
            name='section',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='student',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='student',
            name='guardian_contact',
            field=models.CharField(blank=True, help_text='Guardian contact number (safety).', max_length=20),
        ),
        migrations.AlterField(
            model_name='student',
            name='year_level',
            field=models.CharField(
                blank=True,
                choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')],
                help_text='Year level for reports (1–4).',
                max_length=50,
            ),
        ),
        migrations.RunPython(set_initial_account_status, noop),
    ]
