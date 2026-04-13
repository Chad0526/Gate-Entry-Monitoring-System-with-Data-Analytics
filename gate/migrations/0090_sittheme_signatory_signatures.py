from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0089_alter_adminnotification_notification_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitetheme',
            name='first_signatory_signature',
            field=models.ImageField(blank=True, help_text='Optional image (PNG/JPEG) shown above the 1st signatory line on the back of e-ID cards.', null=True, upload_to='theme/signatures/'),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='second_signatory_signature',
            field=models.ImageField(blank=True, help_text='Optional image shown above the 2nd signatory line on the back of e-ID cards.', null=True, upload_to='theme/signatures/'),
        ),
    ]
