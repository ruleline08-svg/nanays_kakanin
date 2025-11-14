"""
Script to fix existing orders that are incorrectly set to 'ready_for_pickup'
These should be 'pending_confirmation' so admin can review them
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Order

def fix_existing_orders():
    """Update existing ready_for_pickup orders to pending_confirmation"""
    
    # Find all orders that are ready_for_pickup but haven't been confirmed by admin
    ready_orders = Order.objects.filter(status='ready_for_pickup')
    
    print(f"Found {ready_orders.count()} orders with 'ready_for_pickup' status")
    
    if ready_orders.count() == 0:
        print("No orders to fix!")
        return
    
    # Show the orders
    print("\nOrders to update:")
    for order in ready_orders:
        delivery_type = "Delivery" if order.delivery else "Pickup"
        print(f"  - Order #{order.id}: {order.user.username} - {delivery_type} - ₱{order.total_amount}")
    
    # Ask for confirmation
    response = input("\nUpdate these orders to 'pending_confirmation'? (yes/no): ")
    
    if response.lower() == 'yes':
        # Update all orders
        updated_count = ready_orders.update(status='pending_confirmation')
        print(f"\n✅ Updated {updated_count} orders to 'pending_confirmation'")
        print("Admin can now review and confirm these orders.")
    else:
        print("\n❌ Update cancelled. No orders were changed.")

if __name__ == '__main__':
    fix_existing_orders()
