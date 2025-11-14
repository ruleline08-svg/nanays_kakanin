from django.core.management.base import BaseCommand
from kakanin.models import Kakanin


class Command(BaseCommand):
    help = 'Fix all products to be available for reservation'

    def handle(self, *args, **options):
        products = Kakanin.objects.all()
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Found {products.count()} products in database")
        self.stdout.write(f"{'='*60}\n")
        
        # Show current state
        self.stdout.write("\nCurrent state:")
        for product in products:
            self.stdout.write(f"\n{product.name}:")
            self.stdout.write(f"  Categories: {product.categories}")
            self.stdout.write(f"  Stock: {product.stock}")
            self.stdout.write(f"  Allow Reservation: {product.allow_reservation}")
            self.stdout.write(f"  Is Available: {product.is_available}")
            self.stdout.write(f"  Is Reservable: {product.is_reservable()}")
        
        # Fix all products
        self.stdout.write(f"\n\n{'='*60}")
        self.stdout.write("Fixing products...")
        self.stdout.write(f"{'='*60}\n")
        
        fixed_count = 0
        for product in products:
            # Add 'reservation' to categories if not present
            if not product.categories:
                product.categories = ['reservation']
            elif 'reservation' not in product.categories:
                if not isinstance(product.categories, list):
                    product.categories = ['reservation']
                else:
                    product.categories.append('reservation')
            
            # Set stock to 100 if it's 0
            if product.stock == 0:
                product.stock = 100
            
            # Enable reservation
            product.allow_reservation = True
            product.is_available = True
            
            product.save()
            fixed_count += 1
            self.stdout.write(self.style.SUCCESS(f"✓ Fixed: {product.name}"))
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Fixed {fixed_count} products!"))
        self.stdout.write(f"{'='*60}\n")
        
        # Show updated state
        self.stdout.write("\nUpdated products:")
        for product in Kakanin.objects.all():
            status = "✓ RESERVABLE" if product.is_reservable() else "✗ NOT RESERVABLE"
            self.stdout.write(f"  {product.name}:")
            self.stdout.write(f"    Categories: {product.categories}")
            self.stdout.write(f"    Stock: {product.stock}")
            self.stdout.write(f"    Status: {status}")
