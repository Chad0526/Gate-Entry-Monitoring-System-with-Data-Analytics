# Make Event.job_category optional.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0028_visitor_entry_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='job_category',
            field=models.ForeignKey(
                blank=True,
                help_text='Optional. E.g. for tagging events by career type; not used in gate or analytics.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='gate.jobcategory',
            ),
        ),
    ]
