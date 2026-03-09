# Make Event.description optional.

import ckeditor_uploader.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0033_event_image_and_agenda_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='description',
            field=ckeditor_uploader.fields.RichTextUploadingField(blank=True),
        ),
    ]
