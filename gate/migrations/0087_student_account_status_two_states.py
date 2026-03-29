from django.db import migrations, models


def pending_to_inactive(apps, schema_editor):
    Student = apps.get_model('gate', 'Student')
    Student.objects.filter(account_status='PENDING').update(
        account_status='INACTIVE',
        is_active=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0086_auto_20260327_2200'),
    ]

    operations = [
        migrations.RunPython(pending_to_inactive, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='student',
            name='account_status',
            field=models.CharField(
                choices=[('APPROVED', 'Active'), ('INACTIVE', 'Inactive')],
                db_index=True,
                default='APPROVED',
                max_length=10,
            ),
        ),
    ]
