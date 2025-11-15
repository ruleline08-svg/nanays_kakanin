from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Product, Kakanin, AboutPage, ContactInfo, UserProfile, Order, OrderItem, Payment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'preparation_days', 'stock', 'image']
    fields = ['name', 'price', 'preparation_days', 'stock', 'image', 'description']
    readonly_fields = []
@admin.register(Kakanin)
class KakaninAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'preparation_days', 'stock', 'image_preview', 'description_preview')
    list_filter = ('price', 'is_available', 'preparation_days')
    search_fields = ('name', 'description')
    list_editable = ('price', 'preparation_days', 'stock')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'price', 'description', 'image', 'categories')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_days', 'available_from_time', 'available_to_time', 'preparation_days', 'max_daily_quantity')
        }),
        ('Inventory', {
            'fields': ('stock', 'available_today')
        }),
        ('Order Settings', {
            'fields': ('allow_order_now', 'allow_reservation', 'min_order_quantity', 'delivery_min_quantity', 'preorder_downpayment_percent', 'reservation_downpayment_percent'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px; border-radius:5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Image"
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "-"
    description_preview.short_description = "Description"


@admin.register(AboutPage)
class AboutAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at", "photo_preview")
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="height:40px; border-radius:5px;" />', obj.photo.url)
        return "-"
    photo_preview.short_description = "Photo"

@admin.register(ContactInfo)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("address", "phone", "email", "updated_at")
    fieldsets = (
        ('Contact Details', {
            'fields': ('address', 'phone', 'email', 'map_link')
        }),
        ('Social Media', {
            'fields': ('facebook', 'instagram', 'tiktok')
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'barangay', 'zone', 'profile_picture_preview', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone', 'barangay', 'zone')
    list_filter = ('created_at', 'barangay')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'profile_picture', 'phone', 'birth_date')
        }),
        ('Delivery Address (Naval, Biliran)', {
            'fields': ('barangay', 'zone', 'additional_notes'),
            'description': 'Delivery is available only within the Municipality of Naval, Biliran.'
        }),
        ('Legacy Fields', {
            'fields': ('address',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" style="height:40px; border-radius:50%;" />', obj.profile_picture.url)
        return "-"
    profile_picture_preview.short_description = "Profile Picture"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)
    fields = ('product', 'quantity', 'price', 'subtotal')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'payment_method', 'delivery', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'delivery', 'created_at')
    search_fields = ('user__username', 'id', 'gcash_reference')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at', 'payment_proof_preview')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'downpayment_amount', 'shipping_fee')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'gcash_reference', 'payment_proof', 'payment_proof_preview')
        }),
        ('Delivery Options', {
            'fields': ('delivery',)
        }),
        ('Additional Details', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    
    def payment_proof_preview(self, obj):
        if obj.payment_proof:
            return format_html('<img src="{}" style="max-height:200px; border-radius:5px;" />', obj.payment_proof.url)
        return "-"
    payment_proof_preview.short_description = "Payment Proof"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'subtotal')
    list_filter = ('order__created_at',)
    search_fields = ('order__id', 'product__name')
    readonly_fields = ('subtotal',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'reference', 'verified', 'verified_by', 'created_at')
    list_filter = ('verified', 'created_at')
    search_fields = ('order__id', 'reference')
    readonly_fields = ('created_at', 'proof_preview')
    list_editable = ('verified',)
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('order', 'amount', 'reference', 'proof', 'proof_preview')
        }),
        ('Verification', {
            'fields': ('verified', 'verified_by', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def proof_preview(self, obj):
        if obj.proof:
            return format_html('<img src="{}" style="max-height:200px; border-radius:5px;" />', obj.proof.url)
        return "-"
    proof_preview.short_description = "Payment Proof"



