from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0083_gateincident_sas_review_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='semester_transition_status',
            field=models.CharField(
                choices=[
                    ('CLEAR', 'Clear / no semester hold'),
                    ('PENDING_SECOND_SEM', '1st semester completed - pending 2nd semester clearance'),
                    ('SECOND_SEM_CLEARED', '2nd semester cleared'),
                ],
                db_index=True,
                default='CLEAR',
                help_text='Set pending after 1st semester completion to block class entry until cleared for 2nd semester.',
                max_length=30,
            ),
        ),
    ]
