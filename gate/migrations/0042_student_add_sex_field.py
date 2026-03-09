from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0041_add_gateentry_granted_timestamp_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='sex',
            field=models.CharField(
                blank=True,
                choices=[
                    ('MALE', 'Male'),
                    ('FEMALE', 'Female'),
                    ('OTHER', 'Other'),
                    ('PREFER_NOT', 'Prefer not to say'),
                ],
                help_text='Sex/Gender',
                max_length=20,
            ),
        ),
    ]
