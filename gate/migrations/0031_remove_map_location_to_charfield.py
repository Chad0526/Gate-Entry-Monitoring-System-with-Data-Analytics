# Replace Event.location (LocationField) with CharField (no map).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0030_event_location_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='location',
            field=models.CharField(
                blank=True,
                help_text='Optional. e.g. building name or address (no map).',
                max_length=255,
                null=True,
            ),
        ),
    ]
