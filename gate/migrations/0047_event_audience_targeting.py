from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0046_add_supervisor_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='audience_course',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by course / course+year / course+section.', max_length=50),
        ),
        migrations.AddField(
            model_name='event',
            name='audience_scope',
            field=models.CharField(choices=[('all', 'All students'), ('course', 'By course'), ('year_level', 'By year level'), ('course_year', 'By course + year level'), ('course_section', 'By course + section'), ('specific_students', 'Specific students (registration list)')], default='all', help_text='Target audience for this event. Scanner checks student eligibility based on this rule.', max_length=30),
        ),
        migrations.AddField(
            model_name='event',
            name='audience_section',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by course+section.', max_length=30),
        ),
        migrations.AddField(
            model_name='event',
            name='audience_year_level',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by year level / course+year.', max_length=10),
        ),
    ]
