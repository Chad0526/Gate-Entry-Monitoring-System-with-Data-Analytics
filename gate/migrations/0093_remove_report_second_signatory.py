# Single report signatory only (drop second signatory fields)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0092_sittheme_report_signatories'),
    ]

    operations = [
        migrations.RemoveField(model_name='sitetheme', name='report_second_signatory_name'),
        migrations.RemoveField(model_name='sitetheme', name='report_second_signatory_title'),
        migrations.RemoveField(model_name='sitetheme', name='report_second_signatory_signature'),
    ]
