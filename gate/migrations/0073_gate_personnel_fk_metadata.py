# FK/help_text/verbose_name only (after 0072 renames). Avoids SQLite rebuild ordering issues in 0072.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0072_remove_guard_terminology'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gatehandovernote',
            name='shift',
            field=models.ForeignKey(
                blank=True,
                help_text='Shift during which this note was created (null if created outside shift)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='handover_notes',
                to='gate.GateShift',
            ),
        ),
        migrations.AlterField(
            model_name='gatenotification',
            name='broadcast',
            field=models.BooleanField(
                default=False,
                help_text='Send to all on-duty personnel',
            ),
        ),
        migrations.AlterField(
            model_name='gateactivitylog',
            name='personnel',
            field=models.ForeignKey(
                db_index=True,
                help_text='User who performed this action.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='gate_activity_logs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Performed by',
            ),
        ),
        migrations.AlterField(
            model_name='gatehandovernote',
            name='personnel',
            field=models.ForeignKey(
                help_text='User who created this note.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='handover_notes_authored',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Author',
            ),
        ),
        migrations.AlterField(
            model_name='gatehandovernoteread',
            name='personnel',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='handover_note_reads',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Reader',
            ),
        ),
        migrations.AlterField(
            model_name='gatenotification',
            name='notify_user',
            field=models.ForeignKey(
                blank=True,
                help_text='Specific user to notify (null if broadcast).',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='gate_notifications',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Notify user',
            ),
        ),
        migrations.AlterField(
            model_name='gateshift',
            name='personnel',
            field=models.ForeignKey(
                help_text='Personnel user on duty for this shift.',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='gate_shifts',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Personnel on duty',
            ),
        ),
    ]
