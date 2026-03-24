# Rename guard* models/fields to personnel/gate* terminology; preserve all rows.
# Data migration: notification_type and out_reason_code string values, navbar read keys.
# For each model with an index on a renamed FK: RemoveIndex before RenameField, then AddIndex
# (otherwise SQLite migration state can keep index fields named `guard` and fail on rebuild).
# MySQL/InnoDB: cannot drop a composite index if it is the only index covering an FK column;
# we add a temporary single-column index before RemoveIndex, then drop it after AddIndex.
# If 0072 failed mid-way, MySQL may have committed earlier DDL: rerunning must tolerate
# guard_alerted -> staff_alerted already applied (SeparateDatabaseAndState + RunPython).
# Same for RenameModel: table may already be gate_gateshift while django_migrations has no 0072.
# FK help_text/verbose_name updates are in 0073_gate_personnel_fk_metadata.

from django.conf import settings
from django.db import migrations, models
from django.db.utils import OperationalError
import django.db.models.deletion


def _table_exists(cursor, connection, table):
    if connection.vendor == 'mysql':
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            """,
            [table],
        )
        return cursor.fetchone()[0] > 0
    if connection.vendor == 'sqlite':
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type IN ('table', 'view') AND name=%s",
            [table],
        )
        return cursor.fetchone()[0] > 0
    if connection.vendor == 'postgresql':
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = %s
            """,
            [table],
        )
        return cursor.fetchone()[0] > 0
    return False


def _update_content_type_model(schema_editor, app_label, old_model, new_model):
    """django_content_type.model is lowercase, e.g. guardshift -> gateshift."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE django_content_type SET model = %s
            WHERE app_label = %s AND model = %s
            """,
            [new_model, app_label, old_model],
        )


def _idempotent_rename_model_table(apps, schema_editor, old_table, new_table, old_ct_model, new_ct_model):
    """
    RenameModel without failing if new_table already exists (MySQL partial DDL commits).
    Keeps django_content_type in sync.
    """
    connection = schema_editor.connection
    qn = schema_editor.quote_name
    with connection.cursor() as cursor:
        old_exists = _table_exists(cursor, connection, old_table)
        new_exists = _table_exists(cursor, connection, new_table)
    if new_exists and not old_exists:
        _update_content_type_model(schema_editor, 'gate', old_ct_model, new_ct_model)
        return
    if old_exists and not new_exists:
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute(
                    'RENAME TABLE {} TO {}'.format(qn(old_table), qn(new_table)),
                )
            elif connection.vendor == 'sqlite':
                cursor.execute(
                    'ALTER TABLE {} RENAME TO {}'.format(qn(old_table), qn(new_table)),
                )
            elif connection.vendor == 'postgresql':
                cursor.execute(
                    'ALTER TABLE {} RENAME TO {}'.format(qn(old_table), qn(new_table)),
                )
            else:
                raise RuntimeError(
                    'Unsupported database for RenameModel: %s' % connection.vendor
                )
        _update_content_type_model(schema_editor, 'gate', old_ct_model, new_ct_model)
        return
    if old_exists and new_exists:
        raise RuntimeError(
            'Both %s and %s exist; resolve manually before migrating.' % (old_table, new_table)
        )
    raise RuntimeError(
        'Neither %s nor %s exists; fix the database or migration history.' % (old_table, new_table)
    )


def _column_exists(cursor, connection, table, column):
    if connection.vendor == 'mysql':
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        return cursor.fetchone()[0] > 0
    if connection.vendor == 'sqlite':
        # table name is validated (fixed gate_gateincident in callers)
        cursor.execute('PRAGMA table_info(%s)' % connection.ops.quote_name(table))
        return any(row[1] == column for row in cursor.fetchall())
    if connection.vendor == 'postgresql':
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        return cursor.fetchone()[0] > 0
    return False


def _rename_gateincident_guard_alerted_if_needed(apps, schema_editor):
    """
    MySQL commits DDL per statement; if 0072 failed after this rename, rerunning must not
    require guard_alerted to still exist.
    """
    connection = schema_editor.connection
    table = 'gate_gateincident'
    qn = schema_editor.quote_name
    with connection.cursor() as cursor:
        has_old = _column_exists(cursor, connection, table, 'guard_alerted')
        has_new = _column_exists(cursor, connection, table, 'staff_alerted')
    if has_new and not has_old:
        return
    if not has_old:
        raise RuntimeError(
            'gate_gateincident has neither guard_alerted nor staff_alerted; fix the table manually.'
        )
    with connection.cursor() as cursor:
        if connection.vendor == 'mysql':
            cursor.execute(
                'ALTER TABLE {} CHANGE COLUMN {} {} tinyint(1) NOT NULL DEFAULT 1'.format(
                    qn(table), qn('guard_alerted'), qn('staff_alerted'),
                )
            )
        elif connection.vendor == 'sqlite':
            cursor.execute(
                'ALTER TABLE {} RENAME COLUMN {} TO {}'.format(
                    qn(table), qn('guard_alerted'), qn('staff_alerted'),
                )
            )
        elif connection.vendor == 'postgresql':
            cursor.execute(
                'ALTER TABLE {} RENAME COLUMN {} TO {}'.format(
                    qn(table), qn('guard_alerted'), qn('staff_alerted'),
                )
            )
        else:
            raise RuntimeError(
                'Unsupported database for gateincident rename: %s' % connection.vendor
            )


def _mysql_add_simple_index(schema_editor, table, column, index_name):
    """InnoDB needs an index on FK columns; composite index cannot be dropped otherwise."""
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s
            """,
            [table, index_name],
        )
        if cursor.fetchone()[0]:
            return
    qn = schema_editor.quote_name
    try:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE {} ADD INDEX {} ({})'.format(
                    qn(table), qn(index_name), qn(column),
                ),
            )
    except OperationalError as exc:
        # 1061 Duplicate key name (partially applied migration)
        if getattr(exc, 'args', [None])[0] != 1061:
            raise


def _mysql_drop_index_if_exists(schema_editor, table, index_name):
    if schema_editor.connection.vendor != 'mysql':
        return
    qn = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s
            """,
            [table, index_name],
        )
        if cursor.fetchone()[0]:
            cursor.execute(
                'ALTER TABLE {} DROP INDEX {}'.format(qn(table), qn(index_name)),
            )


def forwards_data(apps, schema_editor):
    AdminNotification = apps.get_model('gate', 'AdminNotification')
    GateEntry = apps.get_model('gate', 'GateEntry')
    NotificationRead = apps.get_model('gate', 'NotificationRead')

    AdminNotification.objects.filter(notification_type='staff_guard_registration').update(
        notification_type='staff_personnel_registration',
    )
    AdminNotification.objects.filter(notification_type='guard_alert').update(
        notification_type='personnel_alert',
    )
    GateEntry.objects.filter(out_reason_code='OVERRIDE_BY_GUARD').update(
        out_reason_code='OVERRIDE_BY_PERSONNEL',
    )
    prefix_old = 'notif_staff_guard_'
    prefix_new = 'notif_staff_personnel_'
    for nr in NotificationRead.objects.filter(notification_key__startswith=prefix_old).iterator():
        nr.notification_key = prefix_new + nr.notification_key[len(prefix_old):]
        nr.save(update_fields=['notification_key'])


def noop_reverse(apps, schema_editor):
    pass


def _rename_guardshift_table(apps, schema_editor):
    _idempotent_rename_model_table(
        apps, schema_editor,
        'gate_guardshift', 'gate_gateshift', 'guardshift', 'gateshift',
    )


def _rename_guardnotification_table(apps, schema_editor):
    _idempotent_rename_model_table(
        apps, schema_editor,
        'gate_guardnotification', 'gate_gatenotification',
        'guardnotification', 'gatenotification',
    )


def _rename_guardnote_table(apps, schema_editor):
    _idempotent_rename_model_table(
        apps, schema_editor,
        'gate_guardnote', 'gate_gatehandovernote', 'guardnote', 'gatehandovernote',
    )


def _rename_guardnoteread_table(apps, schema_editor):
    _idempotent_rename_model_table(
        apps, schema_editor,
        'gate_guardnoteread', 'gate_gatehandovernoteread',
        'guardnoteread', 'gatehandovernoteread',
    )


def _rename_guardactivitylog_table(apps, schema_editor):
    _idempotent_rename_model_table(
        apps, schema_editor,
        'gate_guardactivitylog', 'gate_gateactivitylog',
        'guardactivitylog', 'gateactivitylog',
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gate', '0071_rename_staff_guard_profile_to_personnel'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameField(
                    model_name='gateincident',
                    old_name='guard_alerted',
                    new_name='staff_alerted',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_gateincident_guard_alerted_if_needed, noop_reverse),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='GuardShift',
                    new_name='GateShift',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_guardshift_table, noop_reverse),
            ],
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_add_simple_index(se, 'gate_gateshift', 'guard_id', 'tmp_gateshift_guard_fk'),
            noop_reverse,
        ),
        # Drop indexes while the FK column is still `guard_id` so state matches DB; then rename and recreate.
        migrations.RemoveIndex(
            model_name='gateshift',
            name='gate_guards_guard_i_38848e_idx',
        ),
        migrations.RemoveIndex(
            model_name='gateshift',
            name='gate_guards_shift_s_2a41f1_idx',
        ),
        migrations.RenameField(
            model_name='gateshift',
            old_name='guard',
            new_name='personnel',
        ),
        migrations.AddIndex(
            model_name='gateshift',
            index=models.Index(fields=['personnel', '-shift_start'], name='gate_gatesh_personn_9c38d6_idx'),
        ),
        migrations.AddIndex(
            model_name='gateshift',
            index=models.Index(fields=['shift_start', 'shift_end'], name='gate_gatesh_shift_s_6f8224_idx'),
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_drop_index_if_exists(se, 'gate_gateshift', 'tmp_gateshift_guard_fk'),
            noop_reverse,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='GuardNotification',
                    new_name='GateNotification',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_guardnotification_table, noop_reverse),
            ],
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_add_simple_index(
                se, 'gate_gatenotification', 'target_guard_id', 'tmp_gatenotif_tg_fk',
            ),
            noop_reverse,
        ),
        migrations.RemoveIndex(
            model_name='gatenotification',
            name='gate_guardn_target__f3c32b_idx',
        ),
        migrations.RemoveIndex(
            model_name='gatenotification',
            name='gate_guardn_notific_c80d35_idx',
        ),
        migrations.RenameField(
            model_name='gatenotification',
            old_name='target_guard',
            new_name='notify_user',
        ),
        migrations.AddIndex(
            model_name='gatenotification',
            index=models.Index(fields=['notify_user', 'is_read', '-created_at'], name='gate_gateno_notify__61d6e2_idx'),
        ),
        migrations.AddIndex(
            model_name='gatenotification',
            index=models.Index(fields=['notification_type', '-created_at'], name='gate_gateno_notific_47fef4_idx'),
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_drop_index_if_exists(se, 'gate_gatenotification', 'tmp_gatenotif_tg_fk'),
            noop_reverse,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='GuardNote',
                    new_name='GateHandoverNote',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_guardnote_table, noop_reverse),
            ],
        ),
        migrations.RenameField(
            model_name='gatehandovernote',
            old_name='guard',
            new_name='personnel',
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='GuardNoteRead',
                    new_name='GateHandoverNoteRead',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_guardnoteread_table, noop_reverse),
            ],
        ),
        migrations.RenameField(
            model_name='gatehandovernoteread',
            old_name='guard',
            new_name='personnel',
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name='GuardActivityLog',
                    new_name='GateActivityLog',
                ),
            ],
            database_operations=[
                migrations.RunPython(_rename_guardactivitylog_table, noop_reverse),
            ],
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_add_simple_index(
                se, 'gate_gateactivitylog', 'guard_id', 'tmp_gateactlog_guard_fk',
            ),
            noop_reverse,
        ),
        migrations.RemoveIndex(
            model_name='gateactivitylog',
            name='gate_guarda_guard_i_7cbaf5_idx',
        ),
        migrations.RemoveIndex(
            model_name='gateactivitylog',
            name='gate_guarda_action__8da3dd_idx',
        ),
        migrations.RenameField(
            model_name='gateactivitylog',
            old_name='guard',
            new_name='personnel',
        ),
        migrations.AddIndex(
            model_name='gateactivitylog',
            index=models.Index(fields=['personnel', '-timestamp'], name='gate_gateac_personn_3e1232_idx'),
        ),
        migrations.AddIndex(
            model_name='gateactivitylog',
            index=models.Index(fields=['action_type', '-timestamp'], name='gate_gateac_action__4c2906_idx'),
        ),
        migrations.RunPython(
            lambda apps, se: _mysql_drop_index_if_exists(se, 'gate_gateactivitylog', 'tmp_gateactlog_guard_fk'),
            noop_reverse,
        ),
        migrations.RunPython(forwards_data, noop_reverse),
        migrations.AlterField(
            model_name='adminnotification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('student_registration', 'Student Registration'),
                    ('staff_personnel_registration', 'Staff/Faculty/Personnel Registration'),
                    ('incident', 'Incident Alert'),
                    ('capacity', 'Capacity Alert'),
                    ('system', 'System Message'),
                    ('personnel_alert', 'Personnel alert'),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='gateentry',
            name='out_reason_code',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Short code for analytics: LUNCH, NO_CLASS_WINDOW, OVERRIDE_BY_PERSONNEL, etc.',
                max_length=32,
            ),
        ),
    ]
