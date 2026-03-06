# order_tasks.py
import os
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from shop.models import Order

def process_order_automations():
    now = timezone.now()

    # 1. PAID -> SHIPPED (After 30 Minutes)
    paid_time_threshold = now - timedelta(minutes=30)
    orders_to_ship = Order.objects.filter(
        status='PAID', 
        updated_at__lte=paid_time_threshold # Assuming you have an updated_at field
    )
    for order in orders_to_ship:
        order.status = 'SHIPPED'
        order.save()
        print(f"Order #{order.id} automatically SHIPPED.")

    # 2. SHIPPED -> DELIVERED (After 10 Days)
    delivery_threshold = now - timedelta(days=10)
    orders_to_deliver = Order.objects.filter(
        status='SHIPPED',
        updated_at__lte=delivery_threshold
    )
    for order in orders_to_deliver:
        order.status = 'DELIVERED'
        order.save()
        print(f"Order #{order.id} marked as DELIVERED after 10 days.")

if __name__ == "__main__":
    process_order_automations()