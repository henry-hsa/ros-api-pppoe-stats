from django.apps import AppConfig


class MonitorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor_app'

    def ready(self):
        from router_api import updater
        updater.start()
