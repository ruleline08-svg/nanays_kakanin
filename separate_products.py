import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Kakanin

print("\n" + "="*60)
print("SEPARATE ORDER AND RESERVATION PRODUCTS")
print("="*60 + "\n")

# Get all products
products = Kakanin.objects.all()
print(f"Found {products.count()} products in database\n")

if products.count() == 0:
    print("❌ No products found in database!")
    exit()

# Show current state
print("CURRENT PRODUCTS:")
print("-" * 60)
for i, product in enumerate(products, 1):
    print(f"\n{i}. {product.name}")
    print(f"   Categories: {product.categories}")
    print(f"   Stock: {product.stock}")

# Ask user to categorize each product
print("\n" + "="*60)
print("Let's categorize each product:")
print("="*60 + "\n")

for product in products:
    print(f"\n{product.name}:")
    print("  1 = Order Now (immediate purchase, goes to Order Cart)")
    print("  2 = Reservation (advance booking, goes to Reservation Cart)")
    print("  3 = Both (available in both carts)")
    
    while True:
        choice = input(f"Choose category for {product.name} (1/2/3): ").strip()
        
        if choice == '1':
            product.categories = ['order_now']
            product.allow_order_now = True
            product.allow_reservation = False
            print(f"  ✓ Set as ORDER NOW product")
            break
        elif choice == '2':
            product.categories = ['reservation']
            product.allow_order_now = False
            product.allow_reservation = True
            print(f"  ✓ Set as RESERVATION product")
            break
        elif choice == '3':
            product.categories = ['order_now', 'reservation']
            product.allow_order_now = True
            product.allow_reservation = True
            print(f"  ✓ Set as BOTH (Order & Reservation)")
            break
        else:
            print("  ❌ Invalid choice. Please enter 1, 2, or 3")
    
    product.save()

print("\n" + "="*60)
print("✅ PRODUCTS UPDATED!")
print("="*60 + "\n")

# Show final state
print("FINAL CONFIGURATION:")
print("-" * 60)

order_products = []
reservation_products = []

for product in Kakanin.objects.all():
    print(f"\n{product.name}:")
    print(f"  Categories: {product.categories}")
    
    if 'order_now' in product.categories:
        order_products.append(product.name)
        print(f"  ✓ Available in ORDER CART")
    
    if 'reservation' in product.categories:
        reservation_products.append(product.name)
        print(f"  ✓ Available in RESERVATION CART")

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
print(f"\nOrder Cart Products: {', '.join(order_products) if order_products else 'None'}")
print(f"Reservation Cart Products: {', '.join(reservation_products) if reservation_products else 'None'}")
print("\n" + "="*60)
print("Restart your server and refresh the browser!")
print("="*60 + "\n")
