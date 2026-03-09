# Generated migration for adding event FK to GateEntry
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0010_notification_read'),
    ]

    operations = [
        migrations.AddField(
            model_name='gateentry',
            name='event',
            field=models.ForeignKey(blank=True, help_text='Optional: if this scan is for tracking a specific college event (e.g., Founders Day, Field Trip).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gate_entries', to='gate.Event'),
        ),
    ]
