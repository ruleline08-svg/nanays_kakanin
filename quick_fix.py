import sqlite3
import json

# Connect to database
db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "="*60)
print("QUICK FIX: SEPARATE ORDER AND RESERVATION PRODUCTS")
print("="*60 + "\n")

# Get all products
cursor.execute("SELECT id, name, categories, stock FROM kakanin_kakanin")
products = cursor.fetchall()

print("CURRENT PRODUCTS:")
print("-" * 60)
for product_id, name, categories_json, stock in products:
    categories = json.loads(categories_json) if categories_json else []
    print(f"{name}: {categories} (Stock: {stock})")

print("\n" + "="*60)
print("UPDATING...")
print("="*60 + "\n")

# Update Bibingka - ORDER ONLY
cursor.execute("""
    UPDATE kakanin_kakanin 
    SET categories = ?,
        allow_order_now = 1,
        allow_reservation = 0,
        is_available = 1,
        stock = CASE WHEN stock = 0 THEN 100 ELSE stock END
    WHERE name = 'Bibingka'
""", (json.dumps(['order_now']),))
print("✓ Bibingka → ORDER CART only")

# Update Suman - RESERVATION ONLY
cursor.execute("""
    UPDATE kakanin_kakanin 
    SET categories = ?,
        allow_order_now = 0,
        allow_reservation = 1,
        is_available = 1,
        stock = CASE WHEN stock = 0 THEN 100 ELSE stock END
    WHERE name = 'Suman'
""", (json.dumps(['reservation']),))
print("✓ Suman → RESERVATION CART only")

# Commit changes
conn.commit()

# Show updated products
print("\n" + "="*60)
print("UPDATED PRODUCTS:")
print("="*60 + "\n")

cursor.execute("SELECT name, categories, allow_order_now, allow_reservation, stock FROM kakanin_kakanin")
products = cursor.fetchall()

order_products = []
reservation_products = []

for name, categories_json, allow_order, allow_reservation, stock in products:
    categories = json.loads(categories_json) if categories_json else []
    print(f"{name}:")
    print(f"  Categories: {categories}")
    print(f"  Stock: {stock}")
    print(f"  Allow Order: {bool(allow_order)}")
    print(f"  Allow Reservation: {bool(allow_reservation)}")
    
    if 'order_now' in categories:
        order_products.append(name)
    if 'reservation' in categories:
        reservation_products.append(name)
    print()

print("="*60)
print("SUMMARY:")
print("="*60)
print(f"\n📦 ORDER CART: {', '.join(order_products) if order_products else 'None'}")
print(f"📅 RESERVATION CART: {', '.join(reservation_products) if reservation_products else 'None'}")

conn.close()

print("\n" + "="*60)
print("✅ DONE! Restart your Django server and refresh browser")
print("="*60 + "\n")
