"""
Django management command to fix existing orders
Usage: python manage.py fix_orders
"""
from django.core.management.base import BaseCommand
from kakanin.models import Order


class Command(BaseCommand):
    help = 'Fix existing orders that should be pending_confirmation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Automatically update without confirmation',
        )

    def handle(self, *args, **options):
        # Find all orders that are ready_for_pickup
        ready_orders = Order.objects.filter(status='ready_for_pickup')
        
        count = ready_orders.count()
        self.stdout.write(f"\nFound {count} orders with 'ready_for_pickup' status")
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No orders to fix!'))
            return
        
        # Show the orders
        self.stdout.write("\n📋 Orders to update:")
        for order in ready_orders:
            delivery_type = "Delivery" if order.delivery else "Pickup"
            self.stdout.write(f"  • Order #{order.id}: {order.user.username} - {delivery_type} - ₱{order.total_amount}")
        
        # Ask for confirmation unless --auto flag is used
        if not options['auto']:
            confirm = input("\nUpdate these orders to 'pending_confirmation'? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('❌ Cancelled'))
                return
        
        # Update all orders
        updated_count = ready_orders.update(status='pending_confirmation')
        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated_count} orders to "pending_confirmation"'))
        self.stdout.write('Admin can now review and confirm these orders.')
