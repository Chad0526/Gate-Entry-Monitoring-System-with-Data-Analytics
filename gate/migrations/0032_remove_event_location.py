# Remove redundant Event.location (Venue is enough).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0031_remove_map_location_to_charfield'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='location',
        ),
    ]
