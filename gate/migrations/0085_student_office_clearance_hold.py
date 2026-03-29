from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0084_student_semester_transition_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='office_clearance_hold',
            field=models.BooleanField(db_index=True, default=False, help_text='When true, student is blocked from gate entry until office issue is resolved.'),
        ),
        migrations.AddField(
            model_name='student',
            name='office_clearance_note',
            field=models.CharField(blank=True, default='', help_text='Why the office clearance hold was applied.', max_length=255),
        ),
    ]
