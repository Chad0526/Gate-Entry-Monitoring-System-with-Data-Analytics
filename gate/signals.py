"""
Signals for gate models. Keeps User deletion (admin or shell) from failing with
SQLite FOREIGN KEY errors when GateShift rows are removed while GateActivityLog
still points at them via related_shift.

Also clears foreign keys on legacy ``events_*`` SQLite tables: some databases
were created under an old app label and still hold rows/FKs in ``events_*`` while
Django models point at ``gate_*``. Django only updates the latter; SQLite then
rejects ``DELETE FROM auth_user`` with FOREIGN KEY constraint failed.
"""


def _clear_legacy_events_sqlite_user_refs(sender, instance, **kwargs):
    """
    Update or remove rows in legacy ``events_*`` tables that reference this user
    so SQLite FK checks pass before the ORM deletes the User row.
    """
    from django.db import connection

    if connection.vendor != "sqlite":
        return
    uid = instance.pk
    with connection.cursor() as c:
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'events_%'"
        )
        tables = [r[0] for r in c.fetchall()]
    for table in tables:
        with connection.cursor() as c:
            c.execute(
                'PRAGMA foreign_key_list("%s")' % table.replace('"', '""')
            )
            for row in c.fetchall():
                ref_table, from_col, to_col = row[2], row[3], row[4]
                if ref_table != "auth_user" or to_col != "id":
                    continue
                c.execute(
                    'PRAGMA table_info("%s")' % table.replace('"', '""')
                )
                notnull_by_col = {r[1]: r[3] for r in c.fetchall()}
                if notnull_by_col.get(from_col):
                    c.execute(
                        'DELETE FROM "%s" WHERE "%s" = %%s'
                        % (
                            table.replace('"', '""'),
                            from_col.replace('"', '""'),
                        ),
                        [uid],
                    )
                else:
                    c.execute(
                        'UPDATE "%s" SET "%s" = NULL WHERE "%s" = %%s'
                        % (
                            table.replace('"', '""'),
                            from_col.replace('"', '""'),
                            from_col.replace('"', '""'),
                        ),
                        [uid],
                    )


def _clear_gate_shift_fks_before_user_delete(sender, instance, **kwargs):
    """
    Null out FKs from activity logs and notes to this user's shifts before
    CASCADE deletes GateShift, so commit order cannot violate FK constraints.
    """
    from .models import GateActivityLog, GateHandoverNote, GateShift

    shift_ids = list(
        GateShift.objects.filter(personnel=instance).values_list('id', flat=True)
    )
    if shift_ids:
        GateActivityLog.objects.filter(related_shift_id__in=shift_ids).update(
            related_shift=None
        )
        GateHandoverNote.objects.filter(shift_id__in=shift_ids).update(shift=None)

    GateActivityLog.objects.filter(personnel=instance).update(
        related_shift=None,
        related_entry=None,
        related_incident=None,
        related_student=None,
    )


_user_pre_delete_connected = False


def connect_user_signals():
    """Register after Django app registry is ready (called from GateConfig.ready)."""
    global _user_pre_delete_connected
    if _user_pre_delete_connected:
        return
    from django.contrib.auth import get_user_model
    from django.db.models.signals import pre_delete

    User = get_user_model()
    pre_delete.connect(_clear_legacy_events_sqlite_user_refs, sender=User)
    pre_delete.connect(_clear_gate_shift_fks_before_user_delete, sender=User)
    _user_pre_delete_connected = True
