"""Create a database backup (SQLite: copy file; MySQL: mysqldump; PostgreSQL: pg_dump).
Optionally include media files in a tarball. For scheduled backups, use --retain to limit count.
Usage: python manage.py backup_db [--output path] [--with-media] [--retain N]
"""
import glob
import os
import shutil
import tarfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings


def _backups_dir():
    return os.path.join(settings.BASE_DIR, 'backups')


class Command(BaseCommand):
    help = 'Backup database (and optionally media files) for recovery. Schedule with cron or Task Scheduler.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=None,
                            help='Output path. Default: backups/db_YYYYMMDD_HHMMSS.sqlite3 or .sql')
        parser.add_argument('--with-media', action='store_true',
                            help='Also pack MEDIA_ROOT into backups/media_YYYYMMDD_HHMMSS.tar.gz')
        parser.add_argument('--retain', type=int, default=None, metavar='N',
                            help='Keep only the last N DB backups and N media backups; delete older. Good for scheduled runs.')

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        engine = db.get('ENGINE', '')
        out = options.get('output')

        if 'sqlite' in engine:
            path = db.get('NAME', '')
            if not path or not os.path.isabs(path):
                path = os.path.join(settings.BASE_DIR, path)
            if not out:
                os.makedirs(_backups_dir(), exist_ok=True)
                out = os.path.join(_backups_dir(), f"db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3")
            shutil.copy2(path, out)
            self.stdout.write(self.style.SUCCESS(f'Backed up SQLite to {out}'))
        elif 'mysql' in engine:
            if not out:
                os.makedirs(_backups_dir(), exist_ok=True)
                out = os.path.join(_backups_dir(), f"db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
            import subprocess
            name = db.get('NAME', '')
            user = db.get('USER', '')
            password = db.get('PASSWORD', '') or ''
            host = db.get('HOST', '127.0.0.1')
            port = str(db.get('PORT', '3306'))
            env = {**os.environ}
            if password:
                env['MYSQL_PWD'] = password
            try:
                with open(out, 'w', encoding='utf-8', errors='replace') as f:
                    subprocess.run(
                        ['mysqldump', '-h', host, '-P', port, '-u', user, '--single-transaction', '--routines', name],
                        env=env,
                        check=True,
                        stdout=f,
                        stderr=subprocess.PIPE,
                    )
                self.stdout.write(self.style.SUCCESS(f'Backed up MySQL to {out}'))
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.stderr.write(self.style.ERROR(
                    f'MySQL backup failed: {e}. Install mysqldump (MySQL client tools) and check DB_* settings.'
                ))
        else:
            # PostgreSQL: use pg_dump if available
            if not out:
                os.makedirs(_backups_dir(), exist_ok=True)
                out = os.path.join(_backups_dir(), f"db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
            name = db.get('NAME', '')
            user = db.get('USER', '')
            host = db.get('HOST', 'localhost')
            port = db.get('PORT', '5432')
            import subprocess
            try:
                subprocess.run(
                    ['pg_dump', '-h', host, '-p', str(port), '-U', user, '-f', out, name],
                    check=True,
                    capture_output=True,
                    env={**os.environ, 'PGPASSWORD': db.get('PASSWORD', '') or ''},
                )
                self.stdout.write(self.style.SUCCESS(f'Backed up PostgreSQL to {out}'))
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.stderr.write(self.style.ERROR(f'Backup failed: {e}. Install pg_dump and ensure PASSWORD is set.'))

        if options.get('with_media'):
            self._backup_media()

        retain = options.get('retain')
        if retain is not None and retain > 0:
            self._prune_backups(retain)

    def _backup_media(self):
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root or not os.path.isdir(media_root):
            self.stdout.write(self.style.WARNING('MEDIA_ROOT not set or not a directory; skipping media backup.'))
            return
        out_dir = _backups_dir()
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"media_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz")
        try:
            with tarfile.open(out_path, 'w:gz') as tar:
                tar.add(media_root, arcname=os.path.basename(media_root.rstrip(os.sep)))
            self.stdout.write(self.style.SUCCESS(f'Backed up media to {out_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Media backup failed: {e}'))

    def _prune_backups(self, retain):
        """Keep only the last `retain` DB backups and last `retain` media backups (by mtime)."""
        out_dir = _backups_dir()
        if not os.path.isdir(out_dir):
            return
        # DB backups: db_*.sqlite3, db_*.sql
        db_files = (
            glob.glob(os.path.join(out_dir, 'db_*.sqlite3')) +
            glob.glob(os.path.join(out_dir, 'db_*.sql'))
        )
        db_files.sort(key=os.path.getmtime, reverse=True)
        for f in db_files[retain:]:
            try:
                os.remove(f)
                self.stdout.write(f'Pruned old backup: {os.path.basename(f)}')
            except OSError:
                pass
        # Media backups: media_*.tar.gz
        media_files = glob.glob(os.path.join(out_dir, 'media_*.tar.gz'))
        media_files.sort(key=os.path.getmtime, reverse=True)
        for f in media_files[retain:]:
            try:
                os.remove(f)
                self.stdout.write(f'Pruned old backup: {os.path.basename(f)}')
            except OSError:
                pass
