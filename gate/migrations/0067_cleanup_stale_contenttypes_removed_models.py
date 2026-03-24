# Remove ContentType + Permission rows for models that were already deleted from
# gate.models (e.g. load slips, StaffFacultyGuardProfile). Without this, the admin
# "user permissions" filter_horizontal list still shows stale "gate | …" entries.

from django.db import migrations


# ContentType.model values (lowercase) for models removed in earlier migrations.
STALE_GATE_MODELS = (
    'loadslipsubject',
    'studentloadslip',
    'stafffacultyguardprofile',
)


def cleanup_stale_contenttypes(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    qs = ContentType.objects.filter(app_label='gate', model__in=STALE_GATE_MODELS)
    # Deleting ContentType cascades to auth.Permission and M2M group/user links.
    qs.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0066_guard_group_remove_final'),
    ]

    operations = [
        migrations.RunPython(cleanup_stale_contenttypes, noop_reverse),
    ]
