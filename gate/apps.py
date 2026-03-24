from django.apps import AppConfig


class GateConfig(AppConfig):
    name = 'gate'
    verbose_name = 'Gate & Attendance Analytics'

    def ready(self):
        from .signals import connect_user_signals
        connect_user_signals()
