# Sync auth.Permission.name with current model Meta.verbose_name (and custom
# permissions). Old rows still said e.g. "guard shift" after labels were renamed
# to "Gate shift" in code.

from django.apps import apps as django_apps
from django.db import migrations


def refresh_permission_labels(apps, schema_editor):
    from django.contrib.auth.management import _get_all_permissions

    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    gate_config = django_apps.get_app_config('gate')
    for model in gate_config.get_models():
        if model._meta.proxy:
            continue
        ct = ContentType.objects.filter(
            app_label=model._meta.app_label,
            model=model._meta.model_name,
        ).first()
        if not ct:
            continue
        expected = {codename: name for codename, name in _get_all_permissions(model._meta)}
        for perm in Permission.objects.filter(content_type=ct):
            new_name = expected.get(perm.codename)
            if new_name and perm.name != new_name:
                Permission.objects.filter(pk=perm.pk).update(name=new_name)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0067_cleanup_stale_contenttypes_removed_models'),
    ]

    operations = [
        migrations.RunPython(refresh_permission_labels, noop_reverse),
    ]
