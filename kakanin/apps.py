from django.apps import AppConfig


class KakaninConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kakanin'
    
    def ready(self):
        """Import signals when app is ready"""
        import kakanin.signals
