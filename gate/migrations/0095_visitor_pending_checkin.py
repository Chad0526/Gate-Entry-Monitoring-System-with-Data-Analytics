# Generated manually for VisitorPendingCheckin (tablet pre-registration before gate scan)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gate', '0094_alter_adminnotification_notification_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitorPendingCheckin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200)),
                ('purpose', models.CharField(blank=True, max_length=255)),
                ('department', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('photo_in', models.ImageField(blank=True, null=True, upload_to='visitor_pending/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(db_index=True, help_text='After this time the gate treats the pass as needing manual check-in again.')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visitor_pending_checkins', to=settings.AUTH_USER_MODEL)),
                ('pass_obj', models.OneToOneField(help_text='Physical pass the visitor will scan at the gate', on_delete=django.db.models.deletion.CASCADE, related_name='pending_checkin', to='gate.visitorpass')),
            ],
            options={
                'verbose_name': 'visitor pending check-in',
                'verbose_name_plural': 'visitor pending check-ins',
            },
        ),
    ]
