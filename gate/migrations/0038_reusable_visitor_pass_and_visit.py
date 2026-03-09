# Reusable visitor QR pass (VIS-001) + VisitorVisit check-in/check-out lifecycle
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_used_passes_disabled(apps, schema_editor):
    VisitorPass = apps.get_model('gate', 'VisitorPass')
    VisitorPass.objects.filter(used_at__isnull=False).update(status='DISABLED')


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gate', '0037_add_out_reason_code_if_missing'),
    ]

    operations = [
        # VisitorPass: add status, last_used_at; make guest_name/valid_from/valid_until nullable for reusable slots
        migrations.AddField(
            model_name='visitorpass',
            name='status',
            field=models.CharField(
                choices=[('AVAILABLE', 'Available'), ('IN_USE', 'In use'), ('DISABLED', 'Disabled')],
                db_index=True, default='AVAILABLE', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='visitorpass',
            name='last_used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='visitorpass',
            name='guest_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='visitorpass',
            name='valid_from',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='visitorpass',
            name='valid_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # VisitorVisit: one session per check-in/check-out
        migrations.CreateModel(
            name='VisitorVisit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=200)),
                ('purpose', models.CharField(blank=True, max_length=255)),
                ('department', models.CharField(blank=True, max_length=255)),
                ('photo_in', models.ImageField(blank=True, null=True, upload_to='visitor_visits/%Y/%m/')),
                ('photo_out', models.ImageField(blank=True, null=True, upload_to='visitor_visits/%Y/%m/')),
                ('checked_in_at', models.DateTimeField()),
                ('checked_out_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('INSIDE', 'Inside'), ('OUTSIDE', 'Outside')], db_index=True, default='INSIDE', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('id_type', models.CharField(blank=True, max_length=80)),
                ('id_number', models.CharField(blank=True, max_length=120)),
                ('pass_obj', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='gate.VisitorPass')),
                ('checked_in_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visitor_visits_checked_in', to=settings.AUTH_USER_MODEL)),
                ('checked_out_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visitor_visits_checked_out', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Visitor visits',
                'ordering': ['-checked_in_at'],
            },
        ),
        migrations.AddField(
            model_name='visitorpass',
            name='current_visit',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pass_current_for', to='gate.VisitorVisit'),
        ),
        migrations.AddField(
            model_name='gateentry',
            name='visitor_visit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gate_entries', to='gate.VisitorVisit'),
        ),
        migrations.RunPython(set_used_passes_disabled, migrations.RunPython.noop),
    ]
