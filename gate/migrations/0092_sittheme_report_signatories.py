# Report signatories on SiteTheme (separate from e-ID signatories)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0091_alter_adminnotification_notification_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitetheme',
            name='report_first_signatory_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='report_first_signatory_title',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='report_second_signatory_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='report_second_signatory_title',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='report_first_signatory_signature',
            field=models.ImageField(
                blank=True,
                help_text='Optional image for PDF/printed reports (not e-ID cards).',
                null=True,
                upload_to='theme/report_signatures/',
            ),
        ),
        migrations.AddField(
            model_name='sitetheme',
            name='report_second_signatory_signature',
            field=models.ImageField(
                blank=True,
                help_text='Optional image for PDF/printed reports (not e-ID cards).',
                null=True,
                upload_to='theme/report_signatures/',
            ),
        ),
    ]
