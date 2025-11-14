import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Kakanin

print("\n" + "="*60)
print("CONFIGURE PRODUCT CATEGORIES")
print("="*60 + "\n")

# ============================================================
# EDIT THIS SECTION TO SET YOUR PRODUCT CATEGORIES
# ============================================================

# Set which products go where:
# - 'order_now' = Shows in Shop (Order Cart)
# - 'reservation' = Shows in Reservation Shop (Reservation Cart)
# - Both = Shows in both places

PRODUCT_CONFIG = {
    'Bibingka': ['order_now'],        # Only in Order Cart
    'Suman': ['reservation'],          # Only in Reservation Cart
}

# ============================================================
# DON'T EDIT BELOW THIS LINE
# ============================================================

products = Kakanin.objects.all()
print(f"Found {products.count()} products\n")

print("CURRENT STATE:")
print("-" * 60)
for product in products:
    print(f"{product.name}: {product.categories}")

print("\n" + "="*60)
print("UPDATING PRODUCTS...")
print("="*60 + "\n")

updated = 0
for product in products:
    if product.name in PRODUCT_CONFIG:
        new_categories = PRODUCT_CONFIG[product.name]
        
        # Update categories
        product.categories = new_categories
        
        # Update flags based on categories
        product.allow_order_now = 'order_now' in new_categories
        product.allow_reservation = 'reservation' in new_categories
        product.is_available = True
        
        # Ensure stock is set
        if product.stock == 0:
            product.stock = 100
        
        product.save()
        
        print(f"✓ Updated {product.name}:")
        print(f"  Categories: {new_categories}")
        print(f"  Allow Order: {product.allow_order_now}")
        print(f"  Allow Reservation: {product.allow_reservation}")
        print(f"  Stock: {product.stock}")
        print()
        
        updated += 1
    else:
        print(f"⚠ {product.name} not in config - skipped")

print("="*60)
print(f"✅ Updated {updated} products")
print("="*60 + "\n")

# Show final state
print("FINAL CONFIGURATION:")
print("-" * 60)

order_products = []
reservation_products = []

for product in Kakanin.objects.all():
    if 'order_now' in product.categories:
        order_products.append(product.name)
    if 'reservation' in product.categories:
        reservation_products.append(product.name)

print(f"\n📦 ORDER CART (Shop):")
for name in order_products:
    print(f"   - {name}")

print(f"\n📅 RESERVATION CART (Reservation Shop):")
for name in reservation_products:
    print(f"   - {name}")

print("\n" + "="*60)
print("✅ DONE! Restart server and refresh browser")
print("="*60 + "\n")
