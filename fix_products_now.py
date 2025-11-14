import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Kakanin

print("\n" + "="*60)
print("FIXING RESERVATION PRODUCTS")
print("="*60 + "\n")

# Get all products
products = Kakanin.objects.all()
print(f"Found {products.count()} products in database\n")

if products.count() == 0:
    print("❌ No products found in database!")
    print("Please create products first in the admin panel.")
    exit()

# Show current state
print("CURRENT STATE:")
print("-" * 60)
for product in products:
    print(f"\n{product.name}:")
    print(f"  Categories: {product.categories}")
    print(f"  Stock: {product.stock}")
    print(f"  Allow Reservation: {product.allow_reservation}")
    print(f"  Is Available: {product.is_available}")
    print(f"  Is Reservable: {product.is_reservable()}")

# Fix all products
print("\n" + "="*60)
print("FIXING ALL PRODUCTS...")
print("="*60 + "\n")

fixed_count = 0
for product in products:
    changes = []
    
    # Add 'reservation' to categories if not present
    if not product.categories:
        product.categories = ['reservation']
        changes.append("added 'reservation' category")
    elif isinstance(product.categories, list) and 'reservation' not in product.categories:
        product.categories.append('reservation')
        changes.append("added 'reservation' to categories")
    elif not isinstance(product.categories, list):
        product.categories = ['reservation']
        changes.append("fixed categories to list with 'reservation'")
    
    # Set stock to 100 if it's 0
    if product.stock == 0:
        product.stock = 100
        changes.append("set stock to 100")
    
    # Enable reservation
    if not product.allow_reservation:
        product.allow_reservation = True
        changes.append("enabled allow_reservation")
    
    if not product.is_available:
        product.is_available = True
        changes.append("enabled is_available")
    
    if changes:
        product.save()
        fixed_count += 1
        print(f"✓ Fixed {product.name}:")
        for change in changes:
            print(f"    - {change}")
    else:
        print(f"○ {product.name} already configured correctly")

print("\n" + "="*60)
print(f"✅ COMPLETED! Fixed {fixed_count} products")
print("="*60 + "\n")

# Show updated state
print("UPDATED STATE:")
print("-" * 60)
for product in Kakanin.objects.all():
    status = "✓ RESERVABLE" if product.is_reservable() else "✗ NOT RESERVABLE"
    print(f"\n{product.name}: {status}")
    print(f"  Categories: {product.categories}")
    print(f"  Stock: {product.stock}")
    print(f"  Allow Reservation: {product.allow_reservation}")
    print(f"  Is Available: {product.is_available}")

print("\n" + "="*60)
print("Now refresh your browser to see the products!")
print("="*60 + "\n")
