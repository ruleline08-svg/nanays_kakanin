"""
Reservation views for Kakanin products
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from decimal import Decimal
from datetime import date, time, datetime, timedelta
from .models import Kakanin, Reservation, Notification, ContactInfo, ReservationCart, ReservationCartItem


# ---------------------------
# User Reservation Views
# ---------------------------

@login_required
def reservation_shop(request):
    """Redirect to shop page with reservation filter active"""
    from django.urls import reverse
    url = reverse('shop_user') + '?filter=reservation'
    return redirect(url)


@login_required
def add_to_reservation_cart(request, product_id):
    """Add product to reservation cart"""
    product = get_object_or_404(Kakanin, id=product_id)
    
    if not product.is_reservable():
        messages.error(request, 'This product is not available for reservation.')
        return redirect('reservation_shop')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        reservation_date = request.POST.get('reservation_date')
        reservation_time = request.POST.get('reservation_time')
        notes = request.POST.get('notes', '').strip()
        
        # Validation
        if quantity <= 0:
            messages.error(request, 'Quantity must be at least 1.')
            return redirect('reservation_shop')
        
        # Validate minimum order quantity
        min_quantity = product.min_order_quantity if product.min_order_quantity else 1
        if quantity < min_quantity:
            piece_text = "piece" if min_quantity == 1 else "pieces"
            messages.error(request, f'Minimum order quantity for {product.name} is {min_quantity} {piece_text}.')
            return redirect('reservation_shop')
        
        if not reservation_date or not reservation_time:
            messages.error(request, 'Reservation date and time are required.')
            return redirect('reservation_shop')
        
        # Validate reservation date (use product's preparation_days)
        reservation_datetime = datetime.strptime(f"{reservation_date} {reservation_time}", "%Y-%m-%d %H:%M")
        preparation_days = product.preparation_days if product.preparation_days else 3
        min_reservation_date = date.today() + timedelta(days=preparation_days)
        
        if reservation_datetime.date() < min_reservation_date:
            day_text = "day" if preparation_days == 1 else "days"
            messages.error(request, f'Please reserve at least {preparation_days} {day_text} in advance. Earliest date: {min_reservation_date.strftime("%B %d, %Y")}')
            return redirect('reservation_shop')
        
        # Get or create cart
        cart, created = ReservationCart.objects.get_or_create(user=request.user)
        
        # Check if item already exists in cart
        cart_item, created = ReservationCartItem.objects.get_or_create(
            cart=cart,
            product=product,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            defaults={'quantity': quantity, 'notes': notes}
        )
        
        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.notes = notes
            cart_item.save()
            messages.success(request, f'Updated {product.name} quantity in cart!')
        else:
            messages.success(request, f'✅ {product.name} added to reservation cart!')
        
        from django.urls import reverse
        url = reverse('view_cart') + '?tab=reservation'
        return redirect(url)
    
    return redirect('reservation_shop')


@login_required
def reservation_cart(request):
    """Redirect to unified cart with reservation tab active"""
    return redirect('view_cart')


@login_required
def remove_from_reservation_cart(request, item_id):
    """Remove item from reservation cart"""
    cart_item = get_object_or_404(ReservationCartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart.')
    return redirect('view_cart')


@login_required
def update_reservation_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        cart_item = get_object_or_404(ReservationCartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated.')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
    
    return redirect('view_cart')


@login_required
def submit_reservation(request):
    """Submit reservation for admin confirmation (no payment yet)"""
    if request.method != 'POST':
        return redirect('view_cart')
    
    # Get selected item IDs from the form
    selected_item_ids = request.POST.getlist('selected_items')
    
    if not selected_item_ids:
        messages.error(request, 'Please select at least one item to reserve.')
        return redirect('view_cart')
    
    cart = get_object_or_404(ReservationCart, user=request.user)
    
    # Filter cart items to only include selected ones
    cart_items = cart.items.select_related('product').filter(id__in=selected_item_ids)
    
    if not cart_items:
        messages.error(request, 'Selected items not found in your cart.')
        return redirect('view_cart')
    
    try:
        with transaction.atomic():
            # Create reservation for each selected cart item with "pending" status
            for item in cart_items:
                total_amount = item.get_subtotal()
                downpayment_percent = item.product.reservation_downpayment_percent / Decimal('100')
                downpayment_amount = total_amount * downpayment_percent
                
                reservation = Reservation.objects.create(
                    user=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    total_amount=total_amount,
                    downpayment_amount=downpayment_amount,
                    reservation_date=item.reservation_date,
                    reservation_time=item.reservation_time,
                    delivery=False,  # Will be set during payment
                    status='pending',  # Waiting for admin confirmation
                    payment_method='gcash',
                    notes=item.notes
                )
                # Notification automatically created by signal when reservation is created
            
            # Delete only the selected items from cart
            cart_items.delete()
            
            messages.success(request, f'✅ {cart_items.count()} reservation(s) submitted successfully! Please wait for Nanay to confirm your reservation before proceeding to payment.')
            return redirect('reservation_list')
    
    except Exception as e:
        messages.error(request, f'Error submitting reservations: {str(e)}')
        return redirect('view_cart')


@login_required
def reservation_payment(request, reservation_id):
    """Payment page for a reservation ready for payment"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Only allow payment for pending_payment status (after admin confirms)
    if reservation.status != 'pending_payment':
        messages.error(request, 'This reservation is not ready for payment yet.')
        return redirect('view_cart')
    
    if request.method == 'POST':
        gcash_reference = request.POST.get('gcash_reference', '').strip()
        payment_proof = request.FILES.get('payment_proof')
        delivery = request.POST.get('delivery', 'false') == 'true'
        
        if not payment_proof:
            messages.error(request, 'Payment proof is required.')
            return redirect('reservation_payment', reservation_id=reservation_id)
        
        # Validate file
        if payment_proof:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_ext = payment_proof.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                messages.error(request, 'Payment proof must be an image file.')
                return redirect('reservation_payment', reservation_id=reservation_id)
        
        try:
            # Update reservation with payment info
            reservation.gcash_reference = gcash_reference
            reservation.payment_proof = payment_proof
            reservation.delivery = delivery
            reservation.status = 'confirmed'  # Change to confirmed after payment submission
            reservation.save()
            # Notification automatically created by signal when status changes
            
            messages.success(request, f'✅ Payment submitted successfully for Reservation #{reservation.id}! Your reservation is now confirmed.')
            return redirect('reservation_list')
        
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('reservation_payment', reservation_id=reservation_id)
    
    # GET request
    contact_info = ContactInfo.objects.first()
    gcash_number = contact_info.gcash_number if contact_info else '09XX XXX XXXX'
    
    context = {
        'reservation': reservation,
        'gcash_number': gcash_number,
    }
    return render(request, 'kakanin/reservation_payment.html', context)


@login_required
def reservation_checkout(request):
    """Checkout reservation cart"""
    cart = get_object_or_404(ReservationCart, user=request.user)
    cart_items = cart.items.select_related('product').all()
    
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('reservation_shop')
    
    if request.method == 'POST':
        gcash_reference = request.POST.get('gcash_reference', '').strip()
        payment_proof = request.FILES.get('payment_proof')
        delivery = request.POST.get('delivery', 'false') == 'true'
        
        if not payment_proof:
            messages.error(request, 'Payment proof is required.')
            return redirect('reservation_checkout')
        
        # Validate file
        if payment_proof:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_ext = payment_proof.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                messages.error(request, 'Payment proof must be an image file.')
                return redirect('reservation_checkout')
        
        try:
            with transaction.atomic():
                # Create reservation for each cart item
                for item in cart_items:
                    total_amount = item.get_subtotal()
                    downpayment_percent = item.product.reservation_downpayment_percent / Decimal('100')
                    downpayment_amount = total_amount * downpayment_percent
                    
                    reservation = Reservation.objects.create(
                        user=request.user,
                        product=item.product,
                        quantity=item.quantity,
                        total_amount=total_amount,
                        downpayment_amount=downpayment_amount,
                        reservation_date=item.reservation_date,
                        reservation_time=item.reservation_time,
                        delivery=delivery,
                        status='pending_payment',
                        payment_method='gcash',
                        gcash_reference=gcash_reference,
                        payment_proof=payment_proof,
                        notes=item.notes
                    )
                    # Notification automatically created by signal
                
                # Clear cart
                cart.items.all().delete()
                
                messages.success(request, f'✅ {cart_items.count()} reservation(s) submitted successfully! Please wait for admin confirmation.')
                return redirect('reservation_list')
        
        except Exception as e:
            messages.error(request, f'Error processing reservations: {str(e)}')
            return redirect('reservation_checkout')
    
    # GET request
    contact_info = ContactInfo.objects.first()
    gcash_number = contact_info.gcash_number if contact_info else '09XX XXX XXXX'
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': cart.get_total(),
        'downpayment': cart.get_downpayment(),
        'gcash_number': gcash_number,
    }
    return render(request, 'kakanin/reservation_checkout.html', context)


@login_required
def reservation_create(request, product_id):
    """Create a new reservation"""
    product = get_object_or_404(Kakanin, id=product_id)
    
    # Check if product is reservable
    if not product.is_reservable():
        messages.error(request, 'This product is not available for reservation.')
        return redirect('reservation_shop')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        reservation_date = request.POST.get('reservation_date')
        reservation_time = request.POST.get('reservation_time')
        notes = request.POST.get('notes', '').strip()
        gcash_reference = request.POST.get('gcash_reference', '').strip()
        payment_proof = request.FILES.get('payment_proof')
        
        # Validation
        if quantity <= 0:
            messages.error(request, 'Quantity must be at least 1.')
            return redirect('reservation_create', product_id=product_id)
        
        if not reservation_date or not reservation_time:
            messages.error(request, 'Reservation date and time are required.')
            return redirect('reservation_create', product_id=product_id)
        
        # Validate reservation date is not in the past
        from datetime import datetime, timedelta
        reservation_datetime = datetime.strptime(f"{reservation_date} {reservation_time}", "%Y-%m-%d %H:%M")
        
        # Calculate minimum allowed date (use product's preparation_days)
        preparation_days = product.preparation_days if product.preparation_days else 3
        min_reservation_date = date.today() + timedelta(days=preparation_days)
        
        if reservation_datetime.date() < date.today():
            messages.error(request, 'Reservation date cannot be in the past.')
            return redirect('reservation_create', product_id=product_id)
        
        # Validate advance reservation rule based on product's preparation time
        if reservation_datetime.date() < min_reservation_date:
            day_text = "day" if preparation_days == 1 else "days"
            messages.error(request, f'Please reserve at least {preparation_days} {day_text} in advance. Earliest pickup date: {min_reservation_date.strftime("%B %d, %Y")}')
            return redirect('reservation_create', product_id=product_id)
        
        # Validate file if provided
        if payment_proof:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_ext = payment_proof.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                messages.error(request, 'Payment proof must be an image file (jpg, jpeg, png, gif, webp).')
                return redirect('reservation_create', product_id=product_id)
            
            if payment_proof.size > 5 * 1024 * 1024:
                messages.error(request, 'Payment proof file size must be less than 5MB.')
                return redirect('reservation_create', product_id=product_id)
        
        # Calculate amounts
        total_amount = product.price * quantity
        downpayment_percent = product.reservation_downpayment_percent / Decimal('100')
        downpayment_amount = total_amount * downpayment_percent
        
        # Create reservation
        reservation = Reservation.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            total_amount=total_amount,
            downpayment_amount=downpayment_amount,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            status='pending_payment',
            payment_method='gcash',
            gcash_reference=gcash_reference,
            payment_proof=payment_proof,
            notes=notes
        )
        # Notification automatically created by signal
        
        messages.success(request, f'✅ Reservation #{reservation.id} submitted successfully! Your reservation request has been received and is pending admin confirmation.')
        return redirect('reservation_list')
    
    # GET request - show form
    contact_info = ContactInfo.objects.first()
    gcash_number = contact_info.gcash_number if contact_info else '09XX XXX XXXX'
    
    context = {
        'product': product,
        'gcash_number': gcash_number,
        'downpayment_percent': 20,
    }
    return render(request, 'kakanin/reservation_form.html', context)


@login_required
def my_reservations(request):
    """View user's reservations"""
    reservations = Reservation.objects.filter(user=request.user).select_related('product')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    context = {
        'reservations': reservations,
        'status_filter': status_filter,
        'status_choices': Reservation.STATUS_CHOICES,
    }
    return render(request, 'kakanin/my_reservations.html', context)


# ---------------------------
# Admin Reservation Views
# ---------------------------

@staff_member_required
def admin_reservations(request):
    """Admin view to manage all reservations with calendar view"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get all reservations sorted by reservation date (oldest first - first come first served)
    reservations = Reservation.objects.all().select_related('user', 'product').order_by('reservation_date', 'reservation_time', 'created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    # Search by user or product
    search_query = request.GET.get('search')
    if search_query:
        reservations = reservations.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Create calendar data - group reservations by date
    today = datetime.now().date()
    calendar_data = defaultdict(list)
    
    # Get reservations for the next 60 days
    future_reservations = Reservation.objects.filter(
        reservation_date__gte=today,
        reservation_date__lte=today + timedelta(days=60)
    ).exclude(status__in=['cancelled', 'rejected']).select_related('user', 'product')
    
    for reservation in future_reservations:
        calendar_data[reservation.reservation_date].append({
            'id': reservation.id,
            'user': reservation.user.username,
            'product': reservation.product.name,
            'time': reservation.reservation_time,
            'status': reservation.status,
            'quantity': reservation.quantity
        })
    
    # Pagination
    paginator = Paginator(reservations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': Reservation.STATUS_CHOICES,
        'calendar_data': dict(calendar_data),
        'today': today,
    }
    return render(request, 'kakanin/admin_reservations.html', context)


@staff_member_required
def admin_reservation_detail(request, reservation_id):
    """Admin view for reservation details with actions"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    context = {
        'reservation': reservation,
        'status_choices': Reservation.STATUS_CHOICES,
    }
    return render(request, 'kakanin/admin_reservation_detail.html', context)


@staff_member_required
def admin_reservation_confirm(request, reservation_id):
    """Confirm a reservation"""
    if request.method != 'POST':
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != 'pending':
        messages.error(request, 'Only pending reservations can be confirmed.')
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    try:
        with transaction.atomic():
            product = reservation.product
            
            # Update reservation status to pending_payment so user can now pay
            reservation.status = 'pending_payment'
            reservation.save()
            # Notification automatically created by signal
        
        messages.success(request, f'Reservation #{reservation.id} confirmed. User can now proceed to payment.')
    except Exception as e:
        messages.error(request, f'Error confirming reservation: {str(e)}')
    
    return redirect('admin_reservation_detail', reservation_id=reservation_id)


@staff_member_required
def admin_reservation_reject(request, reservation_id):
    """Reject a reservation"""
    if request.method != 'POST':
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status not in ['pending_payment', 'pending']:
        messages.error(request, 'Only pending reservations can be rejected.')
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    decision_notes = request.POST.get('decision_notes', '').strip()
    
    # Update reservation status
    reservation.status = 'rejected'
    reservation.decision_notes = decision_notes
    reservation.save()
    
    # Notification automatically created by signal
    
    messages.success(request, f'Reservation #{reservation.id} rejected. User notified.')
    return redirect('admin_reservation_detail', reservation_id=reservation_id)


@staff_member_required
def admin_reservation_complete(request, reservation_id):
    """Mark a reservation as completed"""
    if request.method != 'POST':
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != 'confirmed':
        messages.error(request, 'Only confirmed reservations can be marked as completed.')
        return redirect('admin_reservation_detail', reservation_id=reservation_id)
    
    # Update reservation status
    reservation.status = 'completed'
    reservation.save()
    # Notification automatically created by signal
    
    messages.success(request, f'Reservation #{reservation.id} marked as completed. User notified.')
    return redirect('admin_reservation_detail', reservation_id=reservation_id)


@staff_member_required
@require_POST
def admin_bulk_delete_reservations(request):
    """Bulk delete reservations - only rejected and completed reservations can be deleted"""
    reservation_ids = request.POST.getlist('reservation_ids')
    
    if not reservation_ids:
        messages.error(request, 'No reservations selected.')
        return redirect('admin_reservations')
    
    try:
        # Get the selected reservations
        reservations = Reservation.objects.filter(id__in=reservation_ids)
        
        # Check if any reservation has a status that cannot be deleted
        invalid_reservations = []
        for reservation in reservations:
            if reservation.status not in ['rejected', 'completed']:
                invalid_reservations.append({
                    'id': reservation.id,
                    'status': reservation.get_status_display()
                })
        
        # If there are invalid reservations, show error and don't delete anything
        if invalid_reservations:
            error_messages = []
            for res in invalid_reservations:
                error_messages.append(f"Reservation #{res['id']} ({res['status']})")
            
            messages.error(
                request, 
                f"Cannot delete the following reservations because they are not rejected or completed: {', '.join(error_messages)}. Only rejected and completed reservations can be deleted."
            )
            return redirect('admin_reservations')
        
        # All reservations are valid for deletion
        deleted_count = reservations.delete()[0]
        messages.success(request, f'Successfully deleted {deleted_count} reservation(s).')
        
    except Exception as e:
        messages.error(request, f'Error deleting reservations: {str(e)}')
    
    return redirect('admin_reservations')
