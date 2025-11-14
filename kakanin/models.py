from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    # Naval, Biliran Barangays
    BARANGAY_CHOICES = [
        ('agpangi', 'Agpangi'),
        ('anislagan', 'Anislagan'),
        ('atipolo', 'Atipolo'),
        ('borac', 'Borac'),
        ('cabungaan', 'Cabungaan'),
        ('calumpang', 'Calumpang'),
        ('capiñahan', 'Capiñahan'),
        ('caraycaray', 'Caraycaray'),
        ('catmon', 'Catmon'),
        ('haguikhikan', 'Haguikhikan'),
        ('imelda', 'Imelda'),
        ('larrazabal', 'Larrazabal'),
        ('libtong', 'Libtong'),
        ('libertad', 'Libertad'),
        ('lico', 'Lico'),
        ('lucsoon', 'Lucsoon'),
        ('mabini', 'Mabini'),
        ('padre_inocentes_garcia', 'Padre Inocentes Garcia (Pob.)'),
        ('padre_sergio_eamiguel', 'Padre Sergio Eamiguel'),
        ('sabang', 'Sabang'),
        ('san_pablo', 'San Pablo'),
        ('santo_nino', 'Santo Niño'),
        ('santissimo_rosario', 'Santissimo Rosario Pob. (Santo Rosa)'),
        ('talustusan', 'Talustusan'),
        ('villa_caneja', 'Villa Caneja'),
        ('villa_consuelo', 'Villa Consuelo'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # New Naval, Biliran specific address fields
    barangay = models.CharField(max_length=50, choices=BARANGAY_CHOICES, blank=True, help_text="Barangay in Naval, Biliran")
    zone = models.CharField(max_length=50, blank=True, help_text="Zone/Purok number")
    additional_notes = models.TextField(blank=True, help_text="Nearest landmark or additional directions")
    
    # Legacy address field (kept for backward compatibility)
    address = models.TextField(blank=True)
    
    birth_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_full_address(self):
        """Return formatted full address"""
        parts = []
        if self.zone:
            parts.append(f"Zone {self.zone}")
        if self.barangay:
            parts.append(dict(self.BARANGAY_CHOICES).get(self.barangay, self.barangay))
        parts.append("Naval, Biliran")
        
        address = ", ".join(parts)
        if self.additional_notes:
            address += f"\n({self.additional_notes})"
        return address


class Kakanin(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    CATEGORY_CHOICES = [
        ('available_now', 'Available Now'),
        ('reservation', 'For Reservation'),
        ('order_now', 'Order Now'),
    ]
    
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='kakanin_images/', blank=True, null=True)
    categories = models.JSONField(default=list, blank=True, help_text="Categories of kakanin (can select multiple)")
    
    # Availability fields
    is_available = models.BooleanField(default=True, help_text="Is this product currently available?")
    available_days = models.JSONField(default=list, blank=True, help_text="Days of the week when available")
    available_from_time = models.TimeField(null=True, blank=True, help_text="Available from this time")
    available_to_time = models.TimeField(null=True, blank=True, help_text="Available until this time")
    preparation_time_hours = models.PositiveIntegerField(default=0, help_text="Hours needed to prepare this item")
    preparation_days = models.PositiveIntegerField(default=3, help_text="Days needed to prepare this item (e.g., 2, 3, 5 days)")
    max_daily_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum quantity available per day")

    # Order/Reservation settings - kept for structure but functionality removed
    allow_order_now = models.BooleanField(default=True)
    allow_reservation = models.BooleanField(default=True)
    min_order_quantity = models.PositiveIntegerField(default=1)
    delivery_min_quantity = models.PositiveIntegerField(default=20)
    preorder_downpayment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    reservation_downpayment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)

    # Inventory
    stock = models.PositiveIntegerField(default=0, help_text="Available pieces in stock")
    available_today = models.BooleanField(default=False, help_text="Available for order today")
    
    def __str__(self):
        return self.name
    
    def is_in_stock(self):
        return self.stock > 0
    
    def is_available_now(self):
        """Check if product is available right now"""
        if not self.is_available:
            return False
            
        from datetime import datetime
        now = datetime.now()
        current_day = now.strftime('%A').lower()
        current_time = now.time()
        
        # Check day availability
        if self.available_days and current_day not in self.available_days:
            return False
            
        # Check time availability
        if self.available_from_time and self.available_to_time:
            if not (self.available_from_time <= current_time <= self.available_to_time):
                return False
                
        return True
    
    def get_availability_display(self):
        """Get human-readable availability info"""
        if not self.is_available:
            return "Currently unavailable"
            
        availability_info = []
        
        if self.available_days:
            days = [day.capitalize() for day in self.available_days]
            availability_info.append(f"Available: {', '.join(days)}")
        
        if self.available_from_time and self.available_to_time:
            availability_info.append(f"Time: {self.available_from_time.strftime('%I:%M %p')} - {self.available_to_time.strftime('%I:%M %p')}")
            
        if self.preparation_days > 0:
            day_text = "day" if self.preparation_days == 1 else "days"
            availability_info.append(f"Preparation: {self.preparation_days} {day_text}")
        elif self.preparation_time_hours > 0:
            availability_info.append(f"Preparation: {self.preparation_time_hours} hours")
            
        return " | ".join(availability_info) if availability_info else "Available anytime"
    
    def get_categories_display(self):
        """Get human-readable categories"""
        if not self.categories:
            return "Uncategorized"
        
        category_labels = []
        for category in self.categories:
            for value, label in self.CATEGORY_CHOICES:
                if value == category:
                    category_labels.append(label)
                    break
        
        return ", ".join(category_labels)
    
    def is_reservable(self):
        """Check if product can be reserved"""
        return self.allow_reservation


class AboutPage(models.Model):
    title = models.CharField(max_length=150, default="About Nanay")
    body = models.TextField()
    photo = models.ImageField(upload_to="about/", blank=True, null=True)
    mission = models.TextField(blank=True, null=True)
    vision = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ContactInfo(models.Model):
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    gcash_number = models.CharField(max_length=20, blank=True, help_text="GCash account number for payments")
    map_link = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Contact info"

    def __str__(self):
        return "Contact Info"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('low_stock', 'Low Stock'),
        ('order_submitted', 'Order Submitted'),
        ('payment_pending', 'Payment Pending'),
        ('payment_approved', 'Payment Approved'),
        ('payment_rejected', 'Payment Rejected'),
        ('order_confirmed', 'Order Confirmed'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('reservation_submitted', 'Reservation Submitted'),
        ('reservation_confirmed', 'Reservation Confirmed'),
        ('reservation_rejected', 'Reservation Rejected'),
        ('reservation_completed', 'Reservation Completed'),
        ('feedback', 'Feedback Received'),
    ]
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    message = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', help_text="User to notify (null for admin notifications)")
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', help_text="Related order if applicable")
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', help_text="Related reservation if applicable")
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Message(models.Model):
    sender = models.ForeignKey(
        User, related_name='sent_messages',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    recipient = models.ForeignKey(
        User, related_name='received_messages',
        on_delete=models.CASCADE
    )
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to='message_images/', blank=True, null=True, help_text="Optional image attachment")
    guest_name = models.CharField(max_length=150, blank=True)
    guest_email = models.EmailField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    unsent_for_sender = models.BooleanField(default=False)
    unsent_for_recipient = models.BooleanField(default=False)
    unsent_for_everyone = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sender_label = self.sender.username if self.sender else (self.guest_name or 'Guest')
        return f"From {sender_label} to {self.recipient.username}: {self.subject or self.body[:30]}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pending_confirmation', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    # User-facing status choices (filtered for customer view)
    USER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('cash', 'Cash on Pickup'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Financial details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    downpayment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    gcash_reference = models.CharField(max_length=100, blank=True, help_text="GCash reference number")
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True, help_text="Payment screenshot")
    
    # Delivery options
    delivery = models.BooleanField(default=False, help_text="True for delivery, False for pickup")
    
    # Notes
    notes = models.TextField(blank=True, help_text="Customer notes or special requests")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - ₱{self.total_amount}"
    
    def get_items_total(self):
        """Calculate total from order items"""
        return sum(item.subtotal for item in self.items.all())
    
    def get_grand_total(self):
        """Get grand total including shipping"""
        return self.total_amount + self.shipping_fee


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Kakanin, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of order")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="quantity * price")
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity} (Order #{self.order.id})"
    
    def save(self, *args, **kwargs):
        # Automatically calculate subtotal
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment verification tracking"""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, help_text="Payment reference number")
    proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        status = "Verified" if self.verified else "Pending"
        return f"Payment for Order #{self.order.id} - {status}"


class Feedback(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    # If user is authenticated
    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    # If guest
    guest_name = models.CharField(max_length=150, blank=True)
    guest_email = models.EmailField(blank=True)

    category = models.CharField(max_length=50, blank=True)  # optional classification
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_guest(self):
        return self.sender is None

    def __str__(self):
        who = self.sender.username if self.sender else (self.guest_name or 'Guest')
        return f"Feedback by {who}: {self.body[:30]}"


class Reservation(models.Model):
    """Reservation model for advance kakanin orders"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pending_payment', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    product = models.ForeignKey(Kakanin, on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    downpayment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    delivery = models.BooleanField(default=False, help_text="True for delivery, False for pickup")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='gcash')
    gcash_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.ImageField(upload_to='reservations/', blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Customer notes or special requests")
    decision_notes = models.TextField(blank=True, help_text="Admin decision notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reservation #{self.id} - {self.user.username} - {self.product.name} on {self.reservation_date}"
    
    def get_remaining_balance(self):
        """Calculate remaining balance after downpayment"""
        return self.total_amount - self.downpayment_amount


class ReservationCart(models.Model):
    """Shopping cart for reservations"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reservation_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Reservation Cart - {self.user.username}"
    
    def get_total(self):
        """Calculate total amount for all items in cart"""
        return sum(item.get_subtotal() for item in self.items.all())
    
    def get_downpayment(self):
        """Calculate downpayment based on each product's reservation_downpayment_percent"""
        from decimal import Decimal
        downpayment = Decimal('0')
        for item in self.items.all():
            item_subtotal = item.get_subtotal()
            downpayment_percent = item.product.reservation_downpayment_percent / Decimal('100')
            downpayment += item_subtotal * downpayment_percent
        return downpayment
    
    def get_item_count(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())


class ReservationCartItem(models.Model):
    """Individual items in reservation cart"""
    cart = models.ForeignKey(ReservationCart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Kakanin, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'product', 'reservation_date', 'reservation_time']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity} for {self.reservation_date}"
    
    def get_subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.price * self.quantity


class Rating(models.Model):
    """Rating and review for completed orders"""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='rating')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    
    # Product Quality Rating (1-5 stars)
    product_rating = models.PositiveIntegerField(
        help_text="Product quality rating (1-5 stars)",
        choices=[(i, i) for i in range(1, 6)]
    )
    product_comment = models.TextField(blank=True, help_text="Comments about the product quality")
    
    # Service Rating (1-5 stars) - For both pickup and delivery
    service_rating = models.PositiveIntegerField(
        help_text="Service rating (1-5 stars)",
        choices=[(i, i) for i in range(1, 6)]
    )
    service_comment = models.TextField(blank=True, help_text="Comments about the service")
    
    # Delivery-specific ratings (only for delivery orders)
    delivery_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Delivery service rating (1-5 stars)",
        choices=[(i, i) for i in range(1, 6)]
    )
    delivery_comment = models.TextField(blank=True, help_text="Comments about delivery (timeliness, condition, etc.)")
    
    # Pickup-specific feedback
    pickup_speed_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Pickup confirmation speed (1-5 stars)",
        choices=[(i, i) for i in range(1, 6)]
    )
    
    # Overall experience
    overall_comment = models.TextField(blank=True, help_text="Overall experience and suggestions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Rating for Order #{self.order.id} by {self.user.username}"
    
    def get_average_rating(self):
        """Calculate average rating"""
        ratings = [self.product_rating, self.service_rating]
        if self.order.delivery and self.delivery_rating:
            ratings.append(self.delivery_rating)
        if not self.order.delivery and self.pickup_speed_rating:
            ratings.append(self.pickup_speed_rating)
        return sum(ratings) / len(ratings) if ratings else 0