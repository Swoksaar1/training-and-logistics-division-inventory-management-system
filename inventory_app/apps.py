from django.apps import AppConfig


class InventoryAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory_app"

    def ready(self):
        import inventory_app.signals  # noqa: F401  