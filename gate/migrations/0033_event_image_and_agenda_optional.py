# Make event image and agenda fields optional so create event works without them.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0032_remove_event_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventimage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='event_image/'),
        ),
        migrations.AlterField(
            model_name='eventagenda',
            name='session_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name='eventagenda',
            name='speaker_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name='eventagenda',
            name='start_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='eventagenda',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='eventagenda',
            name='venue_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
