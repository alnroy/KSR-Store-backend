from django.apps import AppConfig


# shop/apps.py
class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = 'Store Management' # This will show up in the sidebar