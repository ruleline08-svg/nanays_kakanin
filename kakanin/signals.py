"""
Signals for automatic notification creation
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Order, Reservation, Notification


# Track previous status to detect changes
@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """Track the previous status before saving"""
    if instance.pk:
        try:
            instance._previous_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(pre_save, sender=Reservation)
def track_reservation_status_change(sender, instance, **kwargs):
    """Track the previous status before saving"""
    if instance.pk:
        try:
            instance._previous_status = Reservation.objects.get(pk=instance.pk).status
        except Reservation.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def create_order_notifications(sender, instance, created, **kwargs):
    """
    Create notifications when order status changes
    - New order: Notify admin
    - Status changes: Notify user
    """
    # Get previous status if it exists
    previous_status = getattr(instance, '_previous_status', None)
    current_status = instance.status
    
    # Skip if status hasn't changed (unless it's a new order)
    if not created and previous_status == current_status:
        return
    
    # NEW ORDER - Notify admin only
    if created:
        customer_name = instance.user.get_full_name() or instance.user.username
        
        if instance.delivery:
            # Delivery order with payment pending
            Notification.objects.create(
                type='payment_pending',
                message=f'Order #{instance.id}: {customer_name} submitted a delivery order with downpayment. Please review.',
                user=None,  # Admin notification
                order=instance
            )
        else:
            # Pickup order
            Notification.objects.create(
                type='order_submitted',
                message=f'Order #{instance.id}: {customer_name} placed a pickup order.',
                user=None,  # Admin notification
                order=instance
            )
        return
    
    # STATUS CHANGES - Notify user (but not if user cancelled their own order)
    if previous_status != current_status:
        # Skip notification if user cancelled their own order
        skip_user_notification = getattr(instance, '_skip_user_notification', False)
        if skip_user_notification:
            return
        
        notification_map = {
            'confirmed': {
                'type': 'order_confirmed',
                'message': f'Order #{instance.id}: Your order has been confirmed!'
            },
            'ready_for_pickup': {
                'type': 'ready_for_pickup',
                'message': f'Order #{instance.id}: Your order is ready for pickup.'
            },
            'out_for_delivery': {
                'type': 'out_for_delivery',
                'message': f'Order #{instance.id}: Your order is out for delivery.'
            },
            'completed': {
                'type': 'order_completed',
                'message': f'Order #{instance.id}: Your order has been completed. Thank you!'
            },
            'cancelled': {
                'type': 'order_cancelled',
                'message': f'Order #{instance.id}: Your order has been cancelled.'
            },
            'rejected': {
                'type': 'payment_rejected',
                'message': f'Order #{instance.id}: Your order payment was rejected.'
            }
        }
        
        if current_status in notification_map:
            notif_data = notification_map[current_status]
            Notification.objects.create(
                type=notif_data['type'],
                message=notif_data['message'],
                user=instance.user,  # User notification
                order=instance
            )


@receiver(post_save, sender=Reservation)
def create_reservation_notifications(sender, instance, created, **kwargs):
    """
    Create notifications when reservation status changes
    - New reservation: Notify admin
    - Status changes: Notify user
    """
    # Get previous status if it exists
    previous_status = getattr(instance, '_previous_status', None)
    current_status = instance.status
    
    # Skip if status hasn't changed (unless it's a new reservation)
    if not created and previous_status == current_status:
        return
    
    # NEW RESERVATION - Notify admin only
    if created:
        customer_name = instance.user.get_full_name() or instance.user.username
        product_name = instance.product.name if instance.product else "Unknown Product"
        
        Notification.objects.create(
            type='reservation_submitted',
            message=f'Reservation #{instance.id}: {customer_name} submitted a reservation for {product_name} on {instance.reservation_date}.',
            user=None,  # Admin notification
            reservation=instance
        )
        return
    
    # STATUS CHANGES - Notify user (but not if user cancelled their own reservation)
    if previous_status != current_status:
        # Skip notification if user cancelled their own reservation
        skip_user_notification = getattr(instance, '_skip_user_notification', False)
        if skip_user_notification:
            return
        
        product_name = instance.product.name if instance.product else "your product"
        
        notification_map = {
            'confirmed': {
                'type': 'reservation_confirmed',
                'message': f'Reservation #{instance.id}: Your reservation for {product_name} on {instance.reservation_date} at {instance.reservation_time} has been confirmed! Please proceed to payment.'
            },
            'rejected': {
                'type': 'reservation_rejected',
                'message': f'Reservation #{instance.id}: Your reservation for {product_name} was rejected.'
            },
            'completed': {
                'type': 'reservation_completed',
                'message': f'Reservation #{instance.id}: Your reservation has been completed. Thank you!'
            },
            'cancelled': {
                'type': 'order_cancelled',
                'message': f'Reservation #{instance.id}: Your reservation has been cancelled.'
            }
        }
        
        if current_status in notification_map:
            notif_data = notification_map[current_status]
            Notification.objects.create(
                type=notif_data['type'],
                message=notif_data['message'],
                user=instance.user,  # User notification
                reservation=instance
            )
