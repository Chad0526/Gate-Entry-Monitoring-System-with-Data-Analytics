from django.apps import AppConfig


class GateConfig(AppConfig):
    # Keep legacy integer PKs/FKs to avoid risky auto-generated BigAutoField migrations on MySQL.
    default_auto_field = 'django.db.models.AutoField'
    name = 'gate'
    verbose_name = 'Gate & Attendance Analytics'

    def ready(self):
        from .signals import connect_user_signals
        connect_user_signals()
