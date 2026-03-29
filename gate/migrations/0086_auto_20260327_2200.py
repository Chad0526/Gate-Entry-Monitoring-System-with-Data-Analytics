from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0085_student_office_clearance_hold'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='audience_course',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by program / program+year / program+section / program+section+year.', max_length=50, verbose_name='Audience program'),
        ),
        migrations.AlterField(
            model_name='event',
            name='audience_scope',
            field=models.CharField(choices=[('all', 'All students'), ('course', 'By program'), ('year_level', 'By year level'), ('course_year', 'By program + year level'), ('course_section', 'By program + section'), ('course_section_year', 'By program + section + year level'), ('specific_students', 'Specific students (registration list)')], default='all', help_text='Target audience for this event. Scanner checks student eligibility based on this rule.', max_length=30),
        ),
        migrations.AlterField(
            model_name='event',
            name='audience_section',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by program+section / program+section+year.', max_length=30),
        ),
        migrations.AlterField(
            model_name='event',
            name='audience_year_level',
            field=models.CharField(blank=True, default='', help_text='Required when audience is by year level / program+year / program+section+year.', max_length=10),
        ),
        migrations.AlterField(
            model_name='student',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Mobile number'),
        ),
        migrations.AlterField(
            model_name='student',
            name='course',
            field=models.CharField(blank=True, choices=[('BST', 'BST'), ('BSE', 'BSE')], max_length=20, verbose_name='Program'),
        ),
        migrations.AlterField(
            model_name='student',
            name='course_or_section',
            field=models.CharField(blank=True, help_text='Legacy: e.g. BSIT-A (for reports by program/section).', max_length=100),
        ),
        migrations.AlterField(
            model_name='student',
            name='guardians_parents',
            field=models.CharField(blank=True, help_text='Guardian(s) or parent(s) name(s)', max_length=255, verbose_name='Guardian / Parent'),
        ),
    ]
