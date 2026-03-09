# Make Event.location optional (before removing map).

from django.db import migrations
import mapbox_location_field.models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0029_event_job_category_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='location',
            field=mapbox_location_field.models.LocationField(
                blank=True,
                help_text='Optional. Click the map to set event location.',
                map_attrs={},
                null=True,
            ),
        ),
    ]
