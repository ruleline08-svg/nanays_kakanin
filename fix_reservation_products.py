"""
Quick script to fix reservation products
Run this with: python manage.py shell < fix_reservation_products.py
"""
from kakanin.models import Kakanin

# Get all products
products = Kakanin.objects.all()

print(f"\n{'='*60}")
print(f"Found {products.count()} products in database")
print(f"{'='*60}\n")

# Show current state
for product in products:
    print(f"Product: {product.name}")
    print(f"  - Categories: {product.categories}")
    print(f"  - Stock: {product.stock}")
    print(f"  - Allow Reservation: {product.allow_reservation}")
    print(f"  - Is Available: {product.is_available}")
    print(f"  - Is Reservable: {product.is_reservable()}")
    print()

# Ask to fix
print("\n" + "="*60)
response = input("Do you want to fix all products for reservation? (yes/no): ")

if response.lower() == 'yes':
    fixed_count = 0
    for product in products:
        # Add 'reservation' to categories if not present
        if not product.categories:
            product.categories = ['reservation']
        elif 'reservation' not in product.categories:
            product.categories.append('reservation')
        
        # Set stock to 100 if it's 0
        if product.stock == 0:
            product.stock = 100
        
        # Enable reservation
        product.allow_reservation = True
        product.is_available = True
        
        product.save()
        fixed_count += 1
        print(f"✓ Fixed: {product.name}")
    
    print(f"\n{'='*60}")
    print(f"✅ Fixed {fixed_count} products!")
    print(f"{'='*60}\n")
    
    # Show updated state
    print("\nUpdated products:")
    for product in Kakanin.objects.all():
        print(f"  - {product.name}: categories={product.categories}, stock={product.stock}, reservable={product.is_reservable()}")
else:
    print("No changes made.")
