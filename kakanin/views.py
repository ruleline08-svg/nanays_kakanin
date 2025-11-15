from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from .forms import SignUpForm, PersonalInfoForm, CredentialsForm
from .models import (
    Kakanin, AboutPage, ContactInfo,
    UserProfile, Message, Feedback, Notification, Order, Reservation, Rating
)
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from datetime import date, timedelta, datetime, time
from django.utils import timezone
import json
from django.conf import settings
from django.shortcuts import render
from decimal import Decimal
import os


def _expire_overdue_reservations():
    # This function is no longer needed but kept for compatibility
    # Will be removed in future cleanup
    pass


def storage_debug(request):
    return JsonResponse({
        "DEFAULT_FILE_STORAGE": settings.DEFAULT_FILE_STORAGE,
        "CLOUD_NAME": settings.CLOUDINARY_STORAGE.get("CLOUD_NAME"),
        "MEDIA_URL": settings.MEDIA_URL,
    })


def can_order_now(product):
    """
    Check if a product can be ordered right now based on time window.
    Returns True if current time is within order window, False otherwise.
    """
    if not product.allow_order_now:
        return False
    
    # Use localtime to get the current time in the configured timezone
    from django.utils import timezone as tz
    now = tz.localtime(tz.now()).time()
    
    # If no time restrictions, allow ordering
    if not product.available_from_time or not product.available_to_time:
        return True
    
    # Check if current time is within the order window
    result = product.available_from_time <= now <= product.available_to_time
    
    # Debug logging
    print(f"DEBUG: Product={product.name}, Now={now}, Start={product.available_from_time}, End={product.available_to_time}, CanOrder={result}")
    
    return result


def get_order_status(product):
    """
    Get the order status for a product.
    Returns: 'can_order', 'order_closed', or 'reservation_only'
    """
    if 'reservation' in product.categories:
        return 'reservation_only'
    
    if 'order_now' in product.categories:
        if can_order_now(product):
            return 'can_order'
        else:
            return 'order_closed'
    
    return 'can_order'


# ----------------- Static Pages -----------------
def index(request):
    # Guest view
    if not request.user.is_authenticated:
        return render(request, "kakanin/index.html")
    # User view
    elif request.user.is_authenticated and not request.user.is_superuser:
        return redirect("index_user")  # Redirect to user dashboard
    # Admin view
    else:
        return redirect("admin_dashboard")  # send admins to custom admin dashboard


def about(request):
    # Unified About template handles guest vs user vs admin layouts
    about_obj = AboutPage.objects.order_by("-updated_at").first()
    return render(request, "kakanin/about.html", {"about": about_obj})


def contact(request):
    """Contact page is guest-only. Authenticated users are redirected to Messages inbox."""
    if request.user.is_authenticated:
        return redirect('messages_inbox')
    contact_obj = ContactInfo.objects.order_by("-updated_at").first()
    return render(request, "kakanin/contact.html", {"contact": contact_obj})


# ----------------- Auth Views -----------------
def signup_view(request):
    """Two-step signup: step 1 (personal info) → step 2 (credentials)."""
    step = request.POST.get("step") or request.GET.get("step") or "1"

    if request.method == "POST":
        # Step 1: collect personal info, store in session and go to step 2
        if step == "1":
            form = PersonalInfoForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data.copy()
                # serialize date field to ISO string for session storage
                if data.get("birth_date"):
                    bd = data.get("birth_date")
                    data["birth_date"] = bd.isoformat() if isinstance(bd, date) else str(bd)
                request.session["signup_personal"] = data
                request.session.modified = True
                return redirect("/signup?step=2")
            # If form is invalid, it will fall through to render with errors
        # Step 2: create the account using stored personal info
        else:
            form = CredentialsForm(request.POST)
            if form.is_valid():
                personal = request.session.get("signup_personal", {})
                user = form.save(commit=False)
                # attach personal info
                user.first_name = personal.get("first_name", "")
                user.last_name = personal.get("last_name", "")
                user.email = personal.get("email", "")
                # default flags
                user.is_superuser = False
                user.is_staff = False
                user.save()

                # profile extras
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.phone = personal.get("phone", "")
                bd = personal.get("birth_date")
                if bd:
                    try:
                        profile.birth_date = date.fromisoformat(bd) if isinstance(bd, str) else bd
                    except Exception:
                        profile.birth_date = None
                # Save address fields to profile
                profile.barangay = personal.get("barangay", "")
                profile.zone = personal.get("zone", "")
                profile.additional_notes = personal.get("additional_notes", "")
                profile.save()

                # cleanup session and log in
                if "signup_personal" in request.session:
                    del request.session["signup_personal"]
                login(request, user)
                return redirect("index")
            # If form is invalid, it will fall through to render with errors
            # The form object already contains the POST data and errors
            return render(request, "kakanin/signup.html", {"form": form, "step": step})
    else:
        # GET: ensure proper step
        if step == "2" and not request.session.get("signup_personal"):
            return redirect("/signup?step=1")

        # Render appropriate step
        if step == "2":
            form = CredentialsForm()
        else:
            form = PersonalInfoForm(initial=request.session.get("signup_personal"))

    return render(request, "kakanin/signup.html", {"form": form, "step": step})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if user exists
        try:
            user_exists = User.objects.get(username=username)
            # User exists, now check password
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                # Redirect based on role
                if user.is_superuser:
                    return redirect("admin_dashboard")  # superuser → custom admin dashboard
                return redirect("index_user")    # normal user → user dashboard
            else:
                # Form is invalid, which means wrong password
                messages.error(request, 'Wrong password. Please try again.')
        except User.DoesNotExist:
            # User doesn't exist
            messages.error(request, 'Username does not exist. Please check your username or sign up.')
            form = AuthenticationForm()
    else:
        form = AuthenticationForm()
    return render(request, "kakanin/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("index")


# ----------------- Shop & Actions -----------------
def shop_view(request):
    """Show shop based on user authentication"""
    if request.user.is_authenticated and not request.user.is_superuser:
        return redirect('shop_user')
    elif request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_products')
    else:
        # Guest users - show guest shop
        kakanins = Kakanin.objects.all()
        return render(request, "kakanin/shop.html", {
            "kakanins": kakanins,
            "is_admin": False,
            "is_authenticated": False,
        })


@login_required
def index_user(request):
    # Make sure only non-admin users land here
    if request.user.is_superuser:
        return redirect("/admin/")
    
    img_dir = os.path.join(settings.BASE_DIR, 'kakanin', 'static', 'kakanin', 'img')
    exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')
    try:
        files = [
            f for f in os.listdir(img_dir)
            if f.lower().endswith(exts) and 'logo' not in f.lower() and 'gcash' not in f.lower()
        ]
    except FileNotFoundError:
        files = []
    # Paths relative to the static root
    kakanin_images = [f'kakanin/img/{name}' for name in files]

    context = {
        'user': request.user,
        'kakanin_images': kakanin_images,
    }
    return render(request, "kakanin/index_user.html", context)


@login_required
def shop_user(request):
    # Make sure only non-admin users land here
    if request.user.is_superuser:
        return redirect("/admin/")
    
    # Get kakanin products that are available
    from django.db.models import Q
    kakanins = Kakanin.objects.filter(Q(is_available=True) | Q(available_today=True))
    
    # Search functionality from navbar
    search_query = request.GET.get('search', '').strip()
    if search_query:
        kakanins = kakanins.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Add order status to each product
    for kakanin in kakanins:
        kakanin.order_status = get_order_status(kakanin)
        kakanin.can_order = can_order_now(kakanin)
    
    # Calculate total cart count (order cart + reservation cart)
    from .models import ReservationCart, Notification, Message
    order_cart_count = len(request.session.get('cart', {}))
    reservation_cart, _ = ReservationCart.objects.get_or_create(user=request.user)
    reservation_cart_count = reservation_cart.items.count()  # Count number of items, not quantity
    total_cart_count = order_cart_count + reservation_cart_count
    
    # Get unread notification count
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()
    
    # Get unread message count
    unread_messages_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    
    # Debug output
    print(f"DEBUG CART COUNT: Order={order_cart_count}, Reservation={reservation_cart_count}, Total={total_cart_count}")
    print(f"DEBUG NOTIFICATIONS: Unread={unread_notifications_count}")
    print(f"DEBUG MESSAGES: Unread={unread_messages_count}")

    context = {
        'user': request.user,
        'kakanins': kakanins,
        'total_cart_count': total_cart_count,
        'order_cart_count': order_cart_count,
        'reservation_cart_count': reservation_cart_count,
        'unread_notifications_count': unread_notifications_count,
        'unread_messages_count': unread_messages_count,
        'search_query': search_query,
    }
    return render(request, "kakanin/shop_user.html", context)


@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Update basic user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()

        # Update profile info
        profile.phone = request.POST.get('phone', '')
        profile.barangay = request.POST.get('barangay', '')
        profile.zone = request.POST.get('zone', '')
        profile.additional_notes = request.POST.get('additional_notes', '')
        birth_date = request.POST.get('birth_date', '')
        if birth_date:
            profile.birth_date = birth_date
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        profile.save()

        # Handle password change
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if current_password and new_password and confirm_password:
            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect!')
                return redirect('user_profile')
            
            # Check if new passwords match
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match!')
                return redirect('user_profile')
            
            # Check password length
            if len(new_password) < 8:
                messages.error(request, 'New password must be at least 8 characters long!')
                return redirect('user_profile')
            
            # Update password
            request.user.set_password(new_password)
            request.user.save()
            
            # Update session to prevent logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Profile and password updated successfully!')
        else:
            messages.success(request, 'Profile updated successfully!')
        
        return redirect('user_profile')

    # Get user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Get user's reservations
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    
    # Get recent notifications for this user (last 10)
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Calculate total cart count (order cart + reservation cart)
    from .models import ReservationCart
    order_cart_count = len(request.session.get('cart', {}))
    reservation_cart, _ = ReservationCart.objects.get_or_create(user=request.user)
    reservation_cart_count = reservation_cart.items.count()
    total_cart_count = order_cart_count + reservation_cart_count
    
    # Get unread notification count
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()
    
    # Get unread message count
    unread_messages_count = Message.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        'user': request.user,
        'profile': profile,
        'orders': orders,
        'reservations': reservations,
        'notifications': notifications,
        'recent_notifications': notifications,  # For navbar dropdown
        'active_section': 'profile',
        'order_status_filter': '',
        'status_choices': Order.USER_STATUS_CHOICES,  # Use user-friendly status choices
        'total_cart_count': total_cart_count,
        'order_cart_count': order_cart_count,
        'reservation_cart_count': reservation_cart_count,
        'unread_notifications_count': unread_notifications_count,
        'unread_messages_count': unread_messages_count,
    }
    return render(request, "kakanin/user_profile.html", context)


@login_required
def user_notifications(request):
    """View all notifications for the user"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read if requested
    if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('user_notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': Notification.objects.filter(user=request.user, read=False).count(),
    }
    return render(request, "kakanin/notifications.html", context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read = True
    notification.save()
    
    # Redirect to the related page based on notification type
    if notification.order:
        # Redirect to order detail page
        return redirect('order_detail', order_id=notification.order.id)
    elif notification.reservation:
        # Redirect to user reservations page
        return redirect('my_reservations')
    else:
        # Default: go back to notifications
        return redirect('user_notifications')


# ----------------- Admin Views -----------------
@staff_member_required
def admin_notifications(request):
    """View all notifications for admin - shows only admin-specific notifications (user=null)"""
    notifications = Notification.objects.filter(user__isnull=True).order_by('-created_at')
    
    # Mark all as read if requested
    if request.method == 'POST' and request.POST.get('action') == 'mark_all_read':
        Notification.objects.filter(user__isnull=True, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('admin_notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': Notification.objects.filter(user__isnull=True, read=False).count(),
    }
    return render(request, "kakanin/admin_notifications.html", context)


@staff_member_required
def admin_mark_notification_read(request, notification_id):
    """Mark a single notification as read (admin version) - only admin notifications"""
    notification = get_object_or_404(Notification, id=notification_id, user__isnull=True)
    notification.read = True
    notification.save()
    
    # Redirect to the related page based on notification type
    if notification.order:
        # Redirect to order detail page
        return redirect('admin_order_detail', order_id=notification.order.id)
    elif notification.reservation:
        # Redirect to reservation detail page
        return redirect('admin_reservation_detail', reservation_id=notification.reservation.id)
    elif notification.type == 'feedback':
        # Redirect to content page with feedback tab
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('admin_content') + '?tab=feedback'
        return HttpResponseRedirect(url)
    elif notification.type == 'low_stock':
        # Redirect to products page
        return redirect('admin_products')
    else:
        # Default: go back to notifications
        return redirect('admin_notifications')



@staff_member_required
def admin_dashboard(request):
    # Dashboard statistics
    total_products = Kakanin.objects.count()
    total_users = User.objects.filter(is_superuser=False).count()
    
    # Notifications - only show admin notifications (user=null)
    notifications = Notification.objects.filter(user__isnull=True, read=False).order_by('-created_at')[:10]
    
    # Order status distribution
    from django.db.models import Count, Sum, F
    order_status_counts = Order.objects.values('status').annotate(count=Count('id'))
    order_status = {
        'pending': 0,
        'to_pay': 0,
        'completed': 0,
        'cancelled': 0,
    }
    for item in order_status_counts:
        status = item['status'].lower().replace(' ', '_')
        if status in order_status:
            order_status[status] = item['count']
        elif status == 'rejected':
            # Count 'rejected' as 'cancelled' for backward compatibility
            order_status['cancelled'] += item['count']
    
    total_orders = sum(order_status.values())
    
    # Reservation status distribution
    reservation_status_counts = Reservation.objects.values('status').annotate(count=Count('id'))
    reservation_status = {
        'pending': 0,
        'confirmed': 0,
        'completed': 0,
        'cancelled': 0,
    }
    for item in reservation_status_counts:
        status = item['status'].lower()
        if status in reservation_status:
            reservation_status[status] = item['count']
        elif status == 'rejected':
            # Count 'rejected' as 'cancelled' for backward compatibility
            reservation_status['cancelled'] += item['count']
    
    total_reservations = sum(reservation_status.values())
    
    # Recent orders for Recent Sales table
    recent_orders = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created_at')[:10]
    
    # Calculate total revenue from completed orders
    total_revenue = Order.objects.filter(status='completed').aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Top selling products
    from django.db.models import Sum
    top_products = Kakanin.objects.annotate(
        total_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__status='completed')),
        total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'), filter=Q(orderitem__order__status='completed'))
    ).filter(total_sold__isnull=False).order_by('-total_sold')[:10]
    
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'notifications': notifications,
        'order_status': order_status,
        'total_orders': total_orders,
        'reservation_status': reservation_status,
        'total_reservations': total_reservations,
        'recent_orders': recent_orders,
        'total_revenue': total_revenue,
        'top_products': top_products,
    }
    return render(request, "kakanin/admin_dashboard.html", context)


@staff_member_required
def admin_products(request):
    products = Kakanin.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, "kakanin/admin_products.html", context)


@staff_member_required
def admin_product_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        category = request.POST.get('category')
        
        # Inventory
        try:
            stock = int(request.POST.get('stock', 0))
        except Exception:
            stock = 0
        
        # Availability fields
        is_available = request.POST.get('is_available') == 'on'
        available_days = request.POST.getlist('available_days')
        
        # Time fields - handle both order_start_time/order_end_time and available_from_time/available_to_time
        available_from_time = request.POST.get('order_start_time') or request.POST.get('available_from_time') or None
        available_to_time = request.POST.get('order_end_time') or request.POST.get('available_to_time') or None
        
        # Order/Reservation fields - kept for product structure but functionality removed
        allow_order_now = request.POST.get('allow_order_now') == 'on'
        allow_reservation = request.POST.get('allow_reservation') == 'on'
        try:
            preparation_time_hours = int(request.POST.get('preparation_time_hours', 0))
        except Exception:
            preparation_time_hours = 0
        try:
            preparation_days = int(request.POST.get('preparation_days', 3))
        except Exception:
            preparation_days = 3
        max_daily_quantity_raw = request.POST.get('max_daily_quantity')
        max_daily_quantity = int(max_daily_quantity_raw) if max_daily_quantity_raw else None
        try:
            min_order_quantity = int(request.POST.get('min_order_quantity', 1))
        except Exception:
            min_order_quantity = 1
        try:
            delivery_min_quantity = int(request.POST.get('delivery_min_quantity', 20))
        except Exception:
            delivery_min_quantity = 20
        try:
            preorder_downpayment_percent = float(request.POST.get('preorder_downpayment_percent', 50))
        except Exception:
            preorder_downpayment_percent = 50.0
        try:
            reservation_downpayment_percent = float(request.POST.get('reservation_downpayment_percent', 20))
        except Exception:
            reservation_downpayment_percent = 20.0
        
        product = Kakanin.objects.create(
            name=name,
            price=price,
            description=description,
            image=image,
            is_available=is_available,
            available_days=available_days,
            available_from_time=available_from_time,
            available_to_time=available_to_time,
            preparation_time_hours=preparation_time_hours,
            preparation_days=preparation_days,
            max_daily_quantity=max_daily_quantity,
            stock=stock,
            allow_order_now=allow_order_now,
            allow_reservation=allow_reservation,
            min_order_quantity=min_order_quantity,
            delivery_min_quantity=delivery_min_quantity,
            preorder_downpayment_percent=preorder_downpayment_percent,
            reservation_downpayment_percent=reservation_downpayment_percent,
        )
        # Map single category to categories list
        if category:
            try:
                product.categories = [category]
                product.save(update_fields=["categories"])
            except Exception:
                pass
        
        messages.success(request, f'Product "{product.name}" created successfully!')
        return redirect('admin_products')
    
    preset_type = request.GET.get('type')
    preset = {
        'category': None,
        'is_available': True,
        'allow_order_now': True,
        'allow_reservation': True,
    }
    if preset_type == 'available_now':
        preset.update({
            'category': 'available_now',
            'is_available': True,
            'allow_order_now': True,
            'allow_reservation': False,
        })
    elif preset_type == 'order_now':
        preset.update({
            'category': 'order_now',
            'is_available': True,
            'allow_order_now': True,
            'allow_reservation': False,
        })
    elif preset_type == 'reservation':
        preset.update({
            'category': 'reservation',
            'is_available': False,
            'allow_order_now': False,
            'allow_reservation': True,
        })
    
    context = {
        'action': 'Create',
        'day_choices': Kakanin.DAYS_OF_WEEK,
        'category_choices': Kakanin.CATEGORY_CHOICES,
        'preset_type': preset_type,
        'preset_category': preset['category'],
        'preset_is_available': preset['is_available'],
        'preset_allow_order_now': preset['allow_order_now'],
        'preset_allow_reservation': preset['allow_reservation'],
    }
    return render(request, "kakanin/admin_product_form.html", context)


@staff_member_required
def admin_product_edit(request, product_id):
    product = get_object_or_404(Kakanin, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.price = request.POST.get('price')
        product.description = request.POST.get('description')
        # Map single category to categories list
        category = request.POST.get('category')
        if category:
            try:
                product.categories = [category]
            except Exception:
                pass
        
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        
        # Inventory
        try:
            product.stock = int(request.POST.get('stock', product.stock or 0))
        except Exception:
            pass
        
        # Availability fields
        product.is_available = request.POST.get('is_available') == 'on'
        product.available_days = request.POST.getlist('available_days')
        
        # Time fields - handle both order_start_time/order_end_time and available_from_time/available_to_time
        product.available_from_time = request.POST.get('order_start_time') or request.POST.get('available_from_time') or None
        product.available_to_time = request.POST.get('order_end_time') or request.POST.get('available_to_time') or None
        try:
            product.preparation_time_hours = int(request.POST.get('preparation_time_hours', 0))
        except Exception:
            product.preparation_time_hours = 0
        try:
            product.preparation_days = int(request.POST.get('preparation_days', 3))
        except Exception:
            product.preparation_days = 3
        max_daily_quantity_raw = request.POST.get('max_daily_quantity')
        product.max_daily_quantity = int(max_daily_quantity_raw) if max_daily_quantity_raw else None

        # Order/Reservation fields - kept for structure
        product.allow_order_now = request.POST.get('allow_order_now') == 'on'
        product.allow_reservation = request.POST.get('allow_reservation') == 'on'
        try:
            product.min_order_quantity = int(request.POST.get('min_order_quantity', 1))
        except Exception:
            product.min_order_quantity = 1
        try:
            product.delivery_min_quantity = int(request.POST.get('delivery_min_quantity', 20))
        except Exception:
            product.delivery_min_quantity = 20
        try:
            product.preorder_downpayment_percent = float(request.POST.get('preorder_downpayment_percent', 50))
        except Exception:
            product.preorder_downpayment_percent = 50.0
        try:
            product.reservation_downpayment_percent = float(request.POST.get('reservation_downpayment_percent', 20))
        except Exception:
            product.reservation_downpayment_percent = 20.0
        
        product.save()
        messages.success(request, f'Product "{product.name}" updated successfully!')
        return redirect('admin_products')
    
    context = {
        'product': product,
        'action': 'Edit',
        'day_choices': Kakanin.DAYS_OF_WEEK,
        'category_choices': Kakanin.CATEGORY_CHOICES,
    }
    return render(request, "kakanin/admin_product_form.html", context)


@staff_member_required
def admin_product_delete(request, product_id):
    product = get_object_or_404(Kakanin, id=product_id)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('admin_products')
    
    context = {'product': product}
    return render(request, "kakanin/admin_product_delete.html", context)


@staff_member_required
def admin_content(request):
    about_page = AboutPage.objects.first()
    contact_info = ContactInfo.objects.first()
    # Recent feedback for dashboard visibility (guard if table not migrated yet)
    try:
        recent_user_feedback = Feedback.objects.filter(sender__isnull=False).order_by('-created_at')[:10]
        recent_guest_feedback = Feedback.objects.filter(sender__isnull=True).order_by('-created_at')[:10]
    except Exception:
        recent_user_feedback = []
        recent_guest_feedback = []
    
    # Get recent ratings separately to avoid breaking if Rating table doesn't exist
    try:
        recent_ratings = Rating.objects.select_related('user', 'order').order_by('-created_at')[:20]
    except Exception as e:
        recent_ratings = []
        print(f"Error loading ratings: {e}")
    
    context = {
        'about_page': about_page,
        'contact_info': contact_info,
        'recent_user_feedback': recent_user_feedback,
        'recent_guest_feedback': recent_guest_feedback,
        'recent_ratings': recent_ratings,
        'feedback_mode': False,
    }
    return render(request, "kakanin/admin_content.html", context)


@staff_member_required
def admin_feedback_list(request):
    """Dedicated admin page to read and delete feedback (no edit)."""
    q = (request.GET.get('q') or '').strip()
    who = request.GET.get('who')  # 'users', 'guests', or None for all

    try:
        items = Feedback.objects.all().order_by('-created_at')
        if who == 'users':
            items = items.filter(sender__isnull=False)
        elif who == 'guests':
            items = items.filter(sender__isnull=True)
        if q:
            items = items.filter(
                Q(body__icontains=q) |
                Q(category__icontains=q) |
                Q(sender__username__icontains=q) |
                Q(guest_name__icontains=q) |
                Q(guest_email__icontains=q)
            )
    except Exception:
        messages.error(request, 'Feedback table not found. Please run migrations.')
        items = []

    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Reuse admin_content template in a special mode
    return render(request, 'kakanin/admin_content.html', {
        'feedback_mode': True,
        'page_obj': page_obj,
        'q': q,
        'who': who,
    })


@staff_member_required
def admin_feedback_delete(request, feedback_id: int):
    if request.method != 'POST':
        from django.urls import reverse
        return redirect(reverse('admin_content') + '?tab=feedback')
    
    try:
        # Get and delete the specific feedback
        fb = get_object_or_404(Feedback, id=feedback_id)
        feedback_info = f"From: {fb.sender.username if fb.sender else fb.guest_name}"
        fb.delete()
        messages.success(request, f'Feedback deleted successfully. ({feedback_info})')
    except Exception as e:
        messages.error(request, f'Error: Feedback not found or already deleted.')
    
    # Redirect back to content page with feedback tab active
    from django.urls import reverse
    return redirect(reverse('admin_content') + '?tab=feedback')


@staff_member_required
def admin_ratings_delete(request):
    """Delete multiple ratings"""
    if request.method != 'POST':
        return redirect(reverse('admin_content') + '?tab=rating')
    
    rating_ids = request.POST.getlist('rating_ids')
    
    if not rating_ids:
        messages.error(request, 'No ratings selected for deletion.')
        return redirect(reverse('admin_content') + '?tab=rating')
    
    try:
        # Delete selected ratings
        deleted_count = Rating.objects.filter(id__in=rating_ids).delete()[0]
        messages.success(request, f'Successfully deleted {deleted_count} rating{"s" if deleted_count > 1 else ""}.')
    except Exception as e:
        messages.error(request, f'Error deleting ratings: {str(e)}')
    
    return redirect(reverse('admin_content') + '?tab=rating')


@staff_member_required
def admin_about_edit(request):
    about_page = AboutPage.objects.first()
    
    if request.method == 'POST':
        if about_page:
            about_page.title = request.POST.get('title')
            about_page.body = request.POST.get('body')
            about_page.mission = request.POST.get('mission')
            about_page.vision = request.POST.get('vision')
            if 'photo' in request.FILES:
                about_page.photo = request.FILES['photo']
            about_page.save()
        else:
            about_page = AboutPage.objects.create(
                title=request.POST.get('title'),
                body=request.POST.get('body'),
                photo=request.FILES.get('photo'),
                mission=request.POST.get('mission') or None,
                vision=request.POST.get('vision') or None,
            )
        
        messages.success(request, 'About page updated successfully!')
        return redirect('admin_content')
    
    # GET: inline editing lives on admin_content page now
    return redirect('admin_content')


@staff_member_required
def admin_about_delete(request):
    """Delete the AboutPage record to support full CRUD."""
    if request.method == 'POST':
        about_page = AboutPage.objects.first()
        if about_page:
            about_page.delete()
            messages.success(request, 'About page deleted successfully!')
        else:
            messages.error(request, 'No About page to delete.')
        return redirect('admin_content')
    return redirect('admin_about_edit')


@staff_member_required
def admin_contact_edit(request):
    contact_info = ContactInfo.objects.first()
    
    if request.method == 'POST':
        if contact_info:
            contact_info.address = request.POST.get('address')
            contact_info.phone = request.POST.get('phone')
            contact_info.email = request.POST.get('email')
            contact_info.gcash_number = request.POST.get('gcash_number', '')
            contact_info.map_link = request.POST.get('map_link')
            contact_info.facebook = request.POST.get('facebook')
            contact_info.instagram = request.POST.get('instagram')
            contact_info.tiktok = request.POST.get('tiktok')
            contact_info.save()
        else:
            contact_info = ContactInfo.objects.create(
                address=request.POST.get('address'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email'),
                gcash_number=request.POST.get('gcash_number', ''),
                map_link=request.POST.get('map_link'),
                facebook=request.POST.get('facebook'),
                instagram=request.POST.get('instagram'),
                tiktok=request.POST.get('tiktok')
            )
        
        messages.success(request, 'Contact information updated successfully!')
        return redirect('admin_content')
    
    # GET: inline editing lives on admin_content page now
    return redirect('admin_contact_edit')


@staff_member_required
def admin_contact_delete(request):
    """Delete ContactInfo record."""
    if request.method == 'POST':
        contact_info = ContactInfo.objects.first()
        if contact_info:
            contact_info.delete()
            messages.success(request, 'Contact information deleted successfully!')
        else:
            messages.error(request, 'No Contact information to delete.')
        return redirect('admin_content')
    return redirect('admin_contact_edit')


@staff_member_required
def admin_users(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, "kakanin/admin_users.html", context)


@staff_member_required
@xframe_options_sameorigin
def admin_user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        phone = request.POST.get('phone', '')
        barangay = request.POST.get('barangay', '')
        zone = request.POST.get('zone', '')
        additional_notes = request.POST.get('additional_notes', '')
        
        # Validation
        if not username or not email or not password1:
            messages.error(request, 'Username, email, and password are required.')
            return render(request, "kakanin/admin_user_create.html")
        
        if not phone or not barangay or not zone:
            messages.error(request, 'Phone, barangay, and zone are required.')
            return render(request, "kakanin/admin_user_create.html")
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, "kakanin/admin_user_create.html")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, "kakanin/admin_user_create.html")
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, "kakanin/admin_user_create.html")
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser
        )
        
        # Create or update profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.barangay = barangay
        profile.zone = zone
        profile.additional_notes = additional_notes
        profile.save()
        
        messages.success(request, f'User "{username}" created successfully!')
        return redirect('admin_users')
    
    return render(request, "kakanin/admin_user_create.html")


@staff_member_required
@xframe_options_sameorigin
def admin_user_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        phone = request.POST.get('phone', '')
        barangay = request.POST.get('barangay', '')
        zone = request.POST.get('zone', '')
        additional_notes = request.POST.get('additional_notes', '')
        
        # Validation
        if not username or not email:
            error_msg = 'Username and email are required.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, "kakanin/admin_user_edit.html", {'user_obj': user_obj})
        
        if not phone or not barangay or not zone:
            error_msg = 'Phone, barangay, and zone are required.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, "kakanin/admin_user_edit.html", {'user_obj': user_obj})
        
        # Check for duplicate username (excluding current user)
        if User.objects.filter(username=username).exclude(id=user_obj.id).exists():
            error_msg = 'Username already exists.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, "kakanin/admin_user_edit.html", {'user_obj': user_obj})
        
        # Check for duplicate email (excluding current user)
        if User.objects.filter(email=email).exclude(id=user_obj.id).exists():
            error_msg = 'Email already exists.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, "kakanin/admin_user_edit.html", {'user_obj': user_obj})
        
        # Password validation if provided
        if password1 and password1 != password2:
            error_msg = 'Passwords do not match.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, "kakanin/admin_user_edit.html", {'user_obj': user_obj})
        
        # Update user
        user_obj.username = username
        user_obj.email = email
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.is_active = is_active
        user_obj.is_staff = is_staff
        user_obj.is_superuser = is_superuser
        
        # Update password if provided
        if password1:
            user_obj.set_password(password1)
        
        user_obj.save()
        
        # Update profile
        profile, created = UserProfile.objects.get_or_create(user=user_obj)
        profile.phone = phone
        profile.barangay = barangay
        profile.zone = zone
        profile.additional_notes = additional_notes
        profile.save()
        
        success_msg = f'User "{username}" updated successfully!'
        if is_ajax:
            return JsonResponse({'success': True, 'message': success_msg})
        
        messages.success(request, success_msg)
        return redirect('admin_users')
    
    context = {'user_obj': user_obj}
    return render(request, "kakanin/admin_user_edit.html", context)


@staff_member_required
def admin_user_toggle(request, user_id):
    if request.method == 'POST':
        user_obj = get_object_or_404(User, id=user_id)
        
        # Prevent disabling superuser accounts
        if user_obj.is_superuser and user_obj.is_active:
            return JsonResponse({'success': False, 'error': 'Cannot deactivate superuser accounts'})
        
        data = json.loads(request.body)
        user_obj.is_active = data.get('is_active', user_obj.is_active)
        user_obj.save()
        
        status = 'activated' if user_obj.is_active else 'deactivated'
        return JsonResponse({'success': True, 'message': f'User {status} successfully'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@staff_member_required
def admin_user_delete(request, user_id):
    if request.method == 'POST':
        user_obj = get_object_or_404(User, id=user_id)
        
        # Prevent deleting superuser accounts
        if user_obj.is_superuser:
            return JsonResponse({'success': False, 'error': 'Cannot delete superuser accounts'})
        
        username = user_obj.username
        user_obj.delete()
        
        return JsonResponse({'success': True, 'message': f'User "{username}" deleted successfully'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# ---------------------------
# Messaging
# ---------------------------

def messages_inbox(request):
    """Show the latest received and sent messages for the logged-in user."""
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to view your inbox.')
        return redirect('login')
    
    received = Message.objects.filter(recipient=request.user).select_related('sender')
    sent = Message.objects.filter(sender=request.user).select_related('recipient')

    # Build a list of recent correspondents with their latest message
    # Key: user id, Value: dict(user, last_message, last_time)
    threads = {}
    # Consider both directions, ordered by newest first to make first hit the latest
    for m in Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('sender', 'recipient').order_by('-created_at'):
        other = m.sender if m.sender_id and m.sender_id != request.user.id else m.recipient
        if other is None:
            continue
        if other.id not in threads:
            # Online if active within last 5 minutes
            last_login = getattr(other, 'last_login', None)
            is_online = bool(last_login and (timezone.now() - last_login) <= timedelta(minutes=5))
            
            # Count unread messages from this user
            unread_count = Message.objects.filter(
                sender=other,
                recipient=request.user,
                is_read=False
            ).count()
            
            threads[other.id] = {
                'user': other,
                'last_message': m,
                'last_time': m.created_at,
                'is_online': is_online,
                'unread_count': unread_count,
            }
    # Preserve ordering by last_time desc
    recent_threads = sorted(threads.values(), key=lambda x: x['last_time'], reverse=True)

    # Keep lightweight recent users for compatibility (can be removed if not used)
    recent_users = [t['user'] for t in recent_threads[:10]]

    # For regular users, provide admin user for easy messaging
    admin_user = None
    if not request.user.is_superuser:
        admin_user = User.objects.filter(is_superuser=True).first()
    
    context = {
        'received': received[:50],
        'sent': sent[:50],
        'recent_users': recent_users,
        'recent_threads': recent_threads,
        'all_users': User.objects.all().order_by('username') if request.user.is_superuser else None,
        'admin_user': admin_user,
    }
    return render(request, 'kakanin/messages_inbox.html', context)


@login_required
def message_thread(request, user_id: int):
    """A two-person thread between the logged-in user and another user."""
    try:
        other_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('messages_inbox')

    # Send new message in this thread
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        subject = request.POST.get('subject', '').strip()
        image = request.FILES.get('image')
        reply_to_id = request.POST.get('reply_to', '').strip()
        
        if body or image:
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(pk=reply_to_id)
                except Message.DoesNotExist:
                    pass
            
            Message.objects.create(
                sender=request.user, 
                recipient=other_user, 
                subject=subject, 
                body=body, 
                image=image,
                reply_to=reply_to
            )
            return redirect('message_thread', user_id=other_user.id)
        else:
            messages.error(request, 'Please enter a message or attach an image.')

    # Get messages, filtering out those unsent for the current user
    thread_messages = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user)
    ).select_related('sender', 'recipient', 'reply_to').order_by('created_at')
    
    # Filter messages based on unsend status
    filtered_messages = []
    for msg in thread_messages:
        # Skip if unsent for everyone
        if msg.unsent_for_everyone:
            # Only show "unsent" placeholder
            filtered_messages.append(msg)
            continue
        # Skip if sender unsent for themselves and current user is sender
        if msg.sender == request.user and msg.unsent_for_sender:
            continue
        # Skip if recipient unsent for themselves and current user is recipient
        if msg.recipient == request.user and msg.unsent_for_recipient:
            continue
        filtered_messages.append(msg)
    
    thread_messages = filtered_messages

    # Mark incoming messages as read
    Message.objects.filter(sender=other_user, recipient=request.user, is_read=False).update(is_read=True)

    # Get all conversation threads for sidebar
    from django.db.models import Max, Count, Case, When, IntegerField
    
    if request.user.is_superuser:
        # Admin sees all users they've messaged with
        user_ids = Message.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).values_list('sender_id', 'recipient_id')
        
        all_user_ids = set()
        for sender_id, recipient_id in user_ids:
            if sender_id != request.user.id:
                all_user_ids.add(sender_id)
            if recipient_id != request.user.id:
                all_user_ids.add(recipient_id)
        
        all_threads = []
        for uid in all_user_ids:
            u = User.objects.get(pk=uid)
            last_msg = Message.objects.filter(
                Q(sender=request.user, recipient=u) | Q(sender=u, recipient=request.user)
            ).order_by('-created_at').first()
            
            unread = Message.objects.filter(sender=u, recipient=request.user, is_read=False).count()
            
            all_threads.append({
                'other_user': u,
                'last_message': last_msg,
                'unread_count': unread
            })
        
        all_threads.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else timezone.now(), reverse=True)
    else:
        # Regular users only see admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            last_msg = Message.objects.filter(
                Q(sender=request.user, recipient=admin_user) | Q(sender=admin_user, recipient=request.user)
            ).order_by('-created_at').first()
            
            unread = Message.objects.filter(sender=admin_user, recipient=request.user, is_read=False).count()
            
            all_threads = [{
                'other_user': admin_user,
                'last_message': last_msg,
                'unread_count': unread
            }]
        else:
            all_threads = []

    return render(request, 'kakanin/messages_thread.html', {
        'other_user': other_user,
        'messages_list': thread_messages,
        'all_threads': all_threads,
    })


@login_required
def edit_message(request, message_id):
    """Edit a message"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        message = Message.objects.get(pk=message_id, sender=request.user)
    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message not found or you do not have permission to edit it'})
    
    new_body = request.POST.get('body', '').strip()
    if not new_body:
        return JsonResponse({'success': False, 'error': 'Message body cannot be empty'})
    
    message.body = new_body
    message.is_edited = True
    message.edited_at = timezone.now()
    message.save()
    
    return JsonResponse({'success': True, 'message': 'Message edited successfully'})


@login_required
def unsend_message(request, message_id):
    """Unsend a message"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        message = Message.objects.get(pk=message_id, sender=request.user)
    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Message not found or you do not have permission to unsend it'})
    
    unsend_type = request.POST.get('unsend_type')  # 'everyone' or 'me'
    
    if unsend_type == 'everyone':
        message.unsent_for_everyone = True
        message.body = "This message was unsent"
        message.image = None
    elif unsend_type == 'me':
        message.unsent_for_sender = True
    else:
        return JsonResponse({'success': False, 'error': 'Invalid unsend type'})
    
    message.save()
    return JsonResponse({'success': True, 'message': 'Message unsent successfully'})


@login_required
def reply_message(request, message_id):
    """Reply to a specific message"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        original_message = Message.objects.get(pk=message_id)
    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Original message not found'})
    
    # Determine recipient
    if original_message.sender == request.user:
        recipient = original_message.recipient
    else:
        recipient = original_message.sender
    
    body = request.POST.get('body', '').strip()
    image = request.FILES.get('image')
    
    if not body and not image:
        return JsonResponse({'success': False, 'error': 'Message body or image is required'})
    
    # Create reply message
    reply = Message.objects.create(
        sender=request.user,
        recipient=recipient,
        body=body,
        image=image,
        reply_to=original_message
    )
    
    return JsonResponse({'success': True, 'message': 'Reply sent successfully'})


def send_message(request):
    """Generic endpoint to send a message. Used by Contact form to send to an admin."""
    if request.method != 'POST':
        # If logged in, go to inbox; otherwise, back to contact
        return redirect('messages_inbox' if request.user.is_authenticated else 'contact')

    # Choose recipient: first superuser
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        messages.error(request, 'No admin user available to receive messages.')
        return redirect('contact')

    subject = (request.POST.get('subject') or '').strip()
    body = (request.POST.get('message') or request.POST.get('body') or '').strip()
    guest_name = (request.POST.get('name') or '').strip()
    guest_email = (request.POST.get('email') or '').strip()
    image = request.FILES.get('image')

    if not body and not image:
        messages.error(request, 'Please enter a message or attach an image.')
        return redirect('contact')

    if request.user.is_authenticated:
        Message.objects.create(sender=request.user, recipient=admin_user, subject=subject, body=body, image=image)
        messages.success(request, 'Your message has been sent!')
        return redirect('messages_inbox')
    else:
        Message.objects.create(sender=None, recipient=admin_user, subject=subject, body=body, image=image,
                               guest_name=guest_name, guest_email=guest_email)
        messages.success(request, 'Your message has been sent! We will get back to you soon.')
        return redirect('contact')


def submit_feedback(request):
    """Accept feedback from users and guests. POST only."""
    if request.method != 'POST':
        # Route users to messages inbox, guests back to contact
        return redirect('messages_inbox' if request.user.is_authenticated else 'contact')

    body = (request.POST.get('message') or request.POST.get('body') or '').strip()
    category = (request.POST.get('category') or '').strip()
    guest_name = (request.POST.get('name') or '').strip()
    guest_email = (request.POST.get('email') or '').strip()

    if not body:
        messages.error(request, 'Please enter your feedback message.')
        return redirect('messages_inbox' if request.user.is_authenticated else 'contact')

    if request.user.is_authenticated:
        feedback = Feedback.objects.create(sender=request.user, body=body, category=category)
        
        # Notify admins about new feedback (user=None for admin notifications)
        Notification.objects.create(
            user=None,
            type='feedback',
            message=f"New feedback from {request.user.username}: {body[:50]}{'...' if len(body) > 50 else ''}"
        )
        
        return redirect('messages_inbox')
    else:
        # Require minimal identity from guests
        if not guest_name or not guest_email:
            messages.error(request, 'Please provide your name and email so we can reach you back.')
            return redirect('contact')
        
        feedback = Feedback.objects.create(sender=None, guest_name=guest_name, guest_email=guest_email, body=body, category=category)
        
        # Notify admins about new guest feedback (user=None for admin notifications)
        Notification.objects.create(
            user=None,
            type='feedback',
            message=f"New feedback from guest {guest_name} ({guest_email}): {body[:50]}{'...' if len(body) > 50 else ''}"
        )
        
        return redirect('contact')


# ---------------------------
# Cart Management (Session-based)
# ---------------------------

@login_required
def add_to_cart(request, product_id):
    """Add a product to the session-based cart"""
    product = get_object_or_404(Kakanin, id=product_id)
    
    # Check if product is available
    if not product.is_available:
        messages.error(request, 'This product is not available for order.')
        return redirect('shop_user')
    
    # Check if product is closed (order time window has passed)
    if 'order_now' in product.categories and not can_order_now(product):
        messages.error(request, 'This product is currently closed and not available for order.')
        return redirect('shop_user')
    
    # Check stock availability
    if product.stock <= 0:
        messages.error(request, 'This product is out of stock.')
        return redirect('shop_user')
    
    # Get quantity from POST data (from modal) or default to 1
    quantity = 1
    order_type = 'pickup'
    
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1
        order_type = request.POST.get('order_type', 'pickup')
    
    # Validate quantity
    if quantity < 1:
        quantity = 1
    
    if quantity > product.stock:
        messages.error(request, f'Cannot add {quantity} pieces. Only {product.stock} available.')
        return redirect('shop_user')
    
    # Initialize cart in session if it doesn't exist
    if 'cart' not in request.session:
        request.session['cart'] = {}
    
    cart = request.session['cart']
    product_id_str = str(product_id)
    
    # Add or update product in cart
    if product_id_str in cart:
        # Update quantity
        new_quantity = cart[product_id_str]['quantity'] + quantity
        if new_quantity > product.stock:
            messages.error(request, f'Cannot add more. Only {product.stock} pieces available.')
            return redirect('shop_user')
        cart[product_id_str]['quantity'] = new_quantity
        cart[product_id_str]['order_type'] = order_type
        messages.success(request, f'Updated {product.name} quantity to {new_quantity} in cart.')
    else:
        cart[product_id_str] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'stock': product.stock,
            'image': product.image.url if product.image else None,
            'order_type': order_type
        }
        messages.success(request, f'{product.name} ({quantity} pcs) added to cart!')
    
    request.session.modified = True
    
    # Check if this is a "Buy Now" action
    if request.method == 'POST' and request.POST.get('buy_now') == 'true':
        return redirect('checkout_cart')
    
    return redirect('shop_user')


@login_required
def view_cart_old(request):
    """View the shopping cart (old version - kept for compatibility)"""
    cart = request.session.get('cart', {})
    
    # Calculate totals
    cart_items = []
    subtotal = Decimal('0.00')
    
    for product_id, item in cart.items():
        item_total = Decimal(item['price']) * item['quantity']
        cart_items.append({
            'product_id': product_id,
            'name': item['name'],
            'price': Decimal(item['price']),
            'quantity': item['quantity'],
            'stock': item.get('stock', 0),
            'image': item.get('image'),
            'total': item_total
        })
        subtotal += item_total
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'cart_count': sum(item['quantity'] for item in cart.values())
    }
    return render(request, 'kakanin/cart.html', context)


@login_required
def update_cart(request, product_id):
    """Update quantity of a product in cart"""
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        product_id_str = str(product_id)
        
        if product_id_str not in cart:
            messages.error(request, 'Product not found in cart.')
            return redirect('view_cart')
        
        try:
            new_quantity = int(request.POST.get('quantity', 1))
            
            if new_quantity <= 0:
                messages.error(request, 'Quantity must be at least 1.')
                return redirect('view_cart')
            
            # Check stock availability and if product is closed
            product = get_object_or_404(Kakanin, id=product_id)
            
            # Check if product is closed (order time window has passed)
            if 'order_now' in product.categories and not can_order_now(product):
                messages.error(request, f'{product.name} is currently closed and cannot be updated. It will be removed from your cart.')
                del cart[product_id_str]
                request.session.modified = True
                return redirect('view_cart')
            
            if new_quantity > product.stock:
                messages.error(request, f'Only {product.stock} pieces available.')
                return redirect('view_cart')
            
            cart[product_id_str]['quantity'] = new_quantity
            cart[product_id_str]['stock'] = product.stock
            request.session.modified = True
            messages.success(request, f'Updated {cart[product_id_str]["name"]} quantity.')
        except ValueError:
            messages.error(request, 'Invalid quantity.')
    
    return redirect('view_cart')


@login_required
def remove_from_cart(request, product_id):
    """Remove a product from cart"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        product_name = cart[product_id_str]['name']
        del cart[product_id_str]
        request.session.modified = True
        messages.success(request, f'{product_name} removed from cart.')
    else:
        messages.error(request, 'Product not found in cart.')
    
    return redirect('view_cart')


@login_required
def clear_cart(request):
    """Clear all items from cart"""
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True
        messages.success(request, 'Cart cleared successfully.')
    return redirect('view_cart')


@login_required
def checkout_cart(request):
    """Checkout and create orders from cart items"""
    from .models import OrderItem, ContactInfo
    
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')
    
    if request.method == 'POST':
        delivery_option = request.POST.get('delivery_option')  # 'delivery' or 'pickup'
        notes = request.POST.get('notes', '').strip()
        
        # Calculate totals
        total_quantity = sum(item['quantity'] for item in cart.values())
        subtotal = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())
        
        # Determine delivery and shipping fee
        is_delivery = (delivery_option == 'delivery')
        shipping_fee = Decimal('0.00')
        
        if is_delivery:
            # Add shipping fee if total quantity < 20
            if total_quantity < 20:
                shipping_fee = Decimal('50.00')  # Default shipping fee
        
        total_amount = subtotal
        downpayment_amount = Decimal('0.00')
        payment_method = 'cash'
        gcash_reference = ''
        payment_proof = None
        
        # Handle delivery payment (requires 50% downpayment via GCash)
        if is_delivery:
            downpayment_amount = (total_amount + shipping_fee) * Decimal('0.50')
            payment_method = 'gcash'
            gcash_reference = request.POST.get('gcash_reference', '').strip()
            payment_proof = request.FILES.get('payment_proof')
            
            if not gcash_reference:
                messages.error(request, 'GCash reference number is required for delivery orders.')
                return redirect('checkout_cart')
            
            if not payment_proof:
                messages.error(request, 'Payment proof is required for delivery orders.')
                return redirect('checkout_cart')
            
            # Validate file type (only images)
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_ext = payment_proof.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                messages.error(request, 'Payment proof must be an image file (jpg, jpeg, png, gif, webp).')
                return redirect('checkout_cart')
            
            # Validate file size (max 5MB)
            if payment_proof.size > 5 * 1024 * 1024:
                messages.error(request, 'Payment proof file size must be less than 5MB.')
                return redirect('checkout_cart')
        
        # Create the order
        # Both pickup and delivery orders start as pending_confirmation
        # Admin must confirm before order is ready
        order_status = 'pending_confirmation'
        
        if is_delivery:
            success_message = 'Your downpayment has been submitted. Please wait for admin confirmation.'
        else:
            success_message = 'Your pickup order has been submitted. Please wait for admin confirmation before pickup.'
        
        order = Order.objects.create(
            user=request.user,
            status=order_status,
            total_amount=total_amount,
            downpayment_amount=downpayment_amount,
            shipping_fee=shipping_fee,
            payment_method=payment_method,
            gcash_reference=gcash_reference,
            payment_proof=payment_proof,
            delivery=is_delivery,
            notes=notes
        )
        
        # Create order items (don't deduct stock yet - wait for admin confirmation)
        for product_id, item in cart.items():
            try:
                product = Kakanin.objects.get(id=product_id)
                
                # Check if product is closed (order time window has passed)
                if 'order_now' in product.categories and not can_order_now(product):
                    messages.error(request, f'{product.name} is currently closed and cannot be ordered.')
                    order.delete()
                    return redirect('view_cart')
                
                # Verify stock availability
                if product.stock < item['quantity']:
                    messages.error(request, f'Not enough stock for {product.name}. Only {product.stock} available.')
                    order.delete()
                    return redirect('view_cart')
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=product.price,
                    subtotal=product.price * item['quantity']
                )
                
            except Kakanin.DoesNotExist:
                messages.error(request, f'Product {item["name"]} no longer exists.')
                order.delete()
                return redirect('view_cart')
        
        # Notification is automatically created by signal when order is created
        
        # Clear cart after successful checkout
        del request.session['cart']
        request.session.modified = True
        
        messages.success(request, f'Order #{order.id} placed successfully! {success_message}')
        
        return redirect('order_detail', order_id=order.id)
    
    # GET request - show checkout page
    cart_items = []
    subtotal = Decimal('0.00')
    total_quantity = 0
    
    for product_id, item in cart.items():
        item_total = Decimal(item['price']) * item['quantity']
        cart_items.append({
            'product_id': product_id,
            'name': item['name'],
            'price': Decimal(item['price']),
            'quantity': item['quantity'],
            'image': item.get('image'),
            'total': item_total
        })
        subtotal += item_total
        total_quantity += item['quantity']
    
    # Calculate potential fees
    shipping_fee = Decimal('50.00') if total_quantity < 20 else Decimal('0.00')
    delivery_downpayment = (subtotal + shipping_fee) * Decimal('0.50')
    
    # Get GCash info from ContactInfo
    contact_info = ContactInfo.objects.first()
    gcash_number = contact_info.gcash_number if contact_info else '09XX XXX XXXX'
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total_quantity': total_quantity,
        'shipping_fee': shipping_fee,
        'delivery_downpayment': delivery_downpayment,
        'gcash_number': gcash_number,
    }
    return render(request, 'kakanin/checkout.html', context)


# ---------------------------
# Order Management
# ---------------------------

@login_required
def create_order(request, product_id):
    """Create a new order for a product - redirects to add to cart"""
    # This view is deprecated - redirect to add to cart instead
    messages.info(request, 'Please use the cart to place orders.')
    return redirect('add_to_cart', product_id=product_id)


@login_required
def order_list(request):
    """Redirect to unified cart - orders are now in My Cart"""
    return redirect('view_cart')


@login_required
def order_detail(request, order_id):
    """View details of a specific order with confirmation option"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Handle order confirmation (Order Received)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm_received':
            # Only allow confirmation if order is ready_for_pickup or out_for_delivery
            if order.status in ['ready_for_pickup', 'out_for_delivery']:
                order.status = 'completed'
                order.save()
                
                # Notify admins
                # Create admin notification (user=None for admin notifications)
                Notification.objects.create(
                    type='order_completed',
                    message=f'Order #{order.id}: {request.user.username} confirmed receipt of their order.',
                    user=None,
                    order=order
                )
                
                messages.success(request, 'Thank you! Your order has been marked as received.')
                return redirect('order_detail', order_id=order.id)
            else:
                messages.error(request, 'This order cannot be confirmed yet.')
                return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
    }
    return render(request, 'kakanin/order_detail.html', context)


@login_required
def reservation_list(request):
    """Redirect to unified cart - reservations are now in My Cart"""
    return redirect('view_cart')


@login_required
def cancel_reservation(request, reservation_id):
    """Cancel a reservation - only allowed for pending and pending_payment status"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Only allow cancellation if reservation is pending or pending_payment
    if reservation.status not in ['pending', 'pending_payment']:
        messages.error(request, 'This reservation cannot be cancelled.')
        return redirect('user_profile')
    
    # Update reservation status to cancelled
    reservation.status = 'cancelled'
    reservation.decision_notes = 'Cancelled by user'
    # Set flag to prevent user notification (since user is cancelling their own reservation)
    reservation._skip_user_notification = True
    reservation.save()
    
    # Notify all admins about the cancellation
    # Create admin notification (user=None for admin notifications)
    Notification.objects.create(
        type='reservation_cancelled',
        message=f'Reservation #{reservation.id}: {request.user.get_full_name() or request.user.username} cancelled their reservation for {reservation.product.name}.',
        user=None,
        reservation=reservation
    )
    
    messages.success(request, f'Reservation #{reservation.id} has been cancelled.')
    return redirect('user_profile')


@login_required
def cancel_order(request, order_id):
    """Cancel an order and restore stock"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Only allow cancellation if order is pending or pending_confirmation
    if order.status not in ['pending', 'pending_confirmation']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('order_detail', order_id=order_id)
    
    if request.method == 'POST':
        # Restore stock for all order items
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        # Update order status
        order.status = 'cancelled'
        # Set flag to prevent user notification (since user is cancelling their own order)
        order._skip_user_notification = True
        order.save()
        
        # Notify all admins about the cancellation
        # Create admin notification (user=None for admin notifications)
        Notification.objects.create(
            type='order_cancelled',
            message=f'Order #{order.id}: {request.user.get_full_name() or request.user.username} cancelled their order.',
            user=None,
            order=order
        )
        
        messages.success(request, f'Order #{order.id} has been cancelled.')
        return redirect('user_profile')
    
    context = {
        'order': order,
    }
    return render(request, 'kakanin/order_cancel.html', context)


# Admin order management
@staff_member_required
def admin_orders(request):
    """Admin view to manage all orders organized by priority"""
    orders = Order.objects.all().select_related('user').prefetch_related('items__product')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Search by user or order ID
    search_query = request.GET.get('search')
    if search_query:
        orders = orders.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # If filtering or searching, use pagination
    if status_filter or search_query:
        paginator = Paginator(orders, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'status_filter': status_filter,
            'search_query': search_query,
            'status_choices': Order.STATUS_CHOICES,
        }
    else:
        # Default view: Organize by status for priority management
        pending_orders = orders.filter(status='pending').order_by('created_at')
        pending_confirmation_orders = orders.filter(status='pending_confirmation').order_by('created_at')
        confirmed_orders = orders.filter(status='confirmed').order_by('created_at')
        ready_orders = orders.filter(status='ready_for_pickup').order_by('created_at')
        delivery_orders = orders.filter(status='out_for_delivery').order_by('created_at')
        completed_orders = orders.filter(status='completed').order_by('-created_at')[:10]  # Show last 10
        rejected_orders = orders.filter(status='rejected').order_by('-created_at')[:10]  # Show last 10
        
        context = {
            'pending_orders': pending_orders,
            'pending_confirmation_orders': pending_confirmation_orders,
            'confirmed_orders': confirmed_orders,
            'ready_orders': ready_orders,
            'delivery_orders': delivery_orders,
            'completed_orders': completed_orders,
            'rejected_orders': rejected_orders,
            'status_filter': status_filter,
            'search_query': search_query,
            'status_choices': Order.STATUS_CHOICES,
        }
    
    return render(request, 'kakanin/admin_orders.html', context)


@staff_member_required
def admin_order_detail(request, order_id):
    """Admin view for order details with status update and actions"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm_payment':
            # Confirm payment and deduct stock with DB transaction
            if order.status == 'pending_confirmation':
                from django.db import transaction
                
                try:
                    with transaction.atomic():
                        # Deduct stock for all order items
                        for item in order.items.all():
                            product = item.product
                            if product.stock >= item.quantity:
                                product.stock -= item.quantity
                                product.save()
                            else:
                                messages.error(request, f'Insufficient stock for {product.name}. Only {product.stock} available.')
                                return redirect('admin_order_detail', order_id=order_id)
                        
                        # Update order status
                        if order.delivery:
                            order.status = 'out_for_delivery'
                            notification_type = 'out_for_delivery'
                            notification_msg = 'Your order has been confirmed and will be delivered soon.'
                        else:
                            order.status = 'ready_for_pickup'
                            notification_type = 'ready_for_pickup'
                            notification_msg = 'Your order is ready for pickup.'
                        
                        order.save()
                        # Notification automatically created by signal
                    
                    messages.success(request, f'Order #{order.id} payment confirmed. Stock deducted. User notified.')
                except Exception as e:
                    messages.error(request, f'Error confirming order: {str(e)}')
            else:
                messages.error(request, 'Order is not pending confirmation.')
        
        elif action == 'reject_payment':
            # Reject payment
            if order.status == 'pending_confirmation':
                order.status = 'rejected'
                order.save()
                # Notification automatically created by signal
                
                messages.success(request, f'Order #{order.id} rejected. User notified.')
            else:
                messages.error(request, 'Order is not pending confirmation.')
        
        elif action == 'mark_ready_pickup':
            # Mark ready for pickup
            order.status = 'ready_for_pickup'
            order.save()
            # Notification automatically created by signal
            
            messages.success(request, f'Order #{order.id} marked as ready for pickup.')
        
        elif action == 'mark_out_delivery':
            # Mark out for delivery
            order.status = 'out_for_delivery'
            order.save()
            # Notification automatically created by signal
            
            messages.success(request, f'Order #{order.id} marked as out for delivery.')
        
        elif action == 'mark_completed':
            # Mark completed
            order.status = 'completed'
            order.save()
            # Notification automatically created by signal
            
            messages.success(request, f'Order #{order.id} marked as completed.')
        
        elif action == 'update_status':
            # Manual status update
            new_status = request.POST.get('status')
            if new_status in dict(Order.STATUS_CHOICES):
                order.status = new_status
                order.save()
                messages.success(request, f'Order #{order.id} status updated to {order.get_status_display()}.')
        
        return redirect('admin_order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'kakanin/admin_order_detail.html', context)


@staff_member_required
def admin_order_delete(request, order_id):
    """Delete an order"""
    if request.method != 'POST':
        return redirect('admin_orders')
    
    order = get_object_or_404(Order, id=order_id)
    order_number = order.id
    
    # Delete the order
    order.delete()
    
    messages.success(request, f'Order #{order_number} has been deleted successfully.')
    return redirect('admin_orders')


@staff_member_required
def admin_bulk_delete_orders(request):
    """Bulk delete orders - only rejected and completed orders can be deleted"""
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        
        if not order_ids:
            messages.error(request, 'No orders selected.')
            return redirect('admin_orders')
        
        try:
            # Get the selected orders
            orders = Order.objects.filter(id__in=order_ids)
            
            # Check if any order has a status that cannot be deleted
            invalid_orders = []
            for order in orders:
                if order.status not in ['rejected', 'completed']:
                    invalid_orders.append({
                        'id': order.id,
                        'status': order.get_status_display()
                    })
            
            # If there are invalid orders, show error and don't delete anything
            if invalid_orders:
                error_messages = []
                for ord in invalid_orders:
                    error_messages.append(f"Order #{ord['id']} ({ord['status']})")
                
                messages.error(
                    request, 
                    f"Cannot delete the following orders because they are not rejected or completed: {', '.join(error_messages)}. Only rejected and completed orders can be deleted."
                )
                return redirect('admin_orders')
            
            # All orders are valid for deletion
            deleted_count = orders.delete()[0]
            messages.success(request, f'Successfully deleted {deleted_count} order(s).')
            
        except Exception as e:
            messages.error(request, f'Error deleting orders: {str(e)}')
        
        return redirect('admin_orders')
    
    return redirect('admin_orders')


# ---------------------------
# Reservation Views (imported from reservation_views module)
# ---------------------------
from .reservation_views import (
    reservation_shop,
    reservation_create,
    my_reservations,
    add_to_reservation_cart,
    reservation_cart,
    remove_from_reservation_cart,
    update_reservation_cart,
    reservation_checkout,
    admin_reservations,
    admin_reservation_detail,
    admin_reservation_confirm,
    admin_reservation_reject,
    admin_reservation_complete,
    admin_bulk_delete_reservations
)


@login_required
def unified_cart(request):
    """Unified cart view showing both order cart and reservation cart"""
    from .models import ReservationCart, ReservationCartItem
    
    # Get order cart from session
    cart = request.session.get('cart', {})
    order_cart_items = []
    order_total = Decimal('0.00')
    closed_products = []
    
    for product_id, item_data in cart.items():
        try:
            product = Kakanin.objects.get(id=product_id)
            
            # Check if product is closed (order time window has passed)
            if 'order_now' in product.categories and not can_order_now(product):
                closed_products.append(product.name)
                continue
            
            quantity = item_data['quantity']
            subtotal = product.price * quantity
            order_cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            order_total += subtotal
        except Kakanin.DoesNotExist:
            continue
    
    # Remove closed products from cart
    if closed_products:
        cart_copy = cart.copy()
        for product_id, item_data in cart_copy.items():
            try:
                product = Kakanin.objects.get(id=product_id)
                if 'order_now' in product.categories and not can_order_now(product):
                    del cart[product_id]
            except Kakanin.DoesNotExist:
                pass
        
        if closed_products:
            request.session.modified = True
            messages.warning(request, f'The following products are now closed and have been removed from your cart: {", ".join(closed_products)}')
    
    # Get reservation cart from database
    reservation_cart, created = ReservationCart.objects.get_or_create(user=request.user)
    reservation_cart_items = reservation_cart.items.select_related('product').all()
    reservation_total = reservation_cart.get_total()
    reservation_downpayment = reservation_cart.get_downpayment()
    
    context = {
        'order_cart_items': order_cart_items,
        'order_cart_count': len(order_cart_items),
        'order_total': order_total,
        'reservation_cart_items': reservation_cart_items,
        'reservation_cart_count': reservation_cart_items.count(),
        'reservation_total': reservation_total,
        'reservation_downpayment': reservation_downpayment,
    }
    
    return render(request, 'kakanin/unified_cart.html', context)


@login_required
def rate_order(request, order_id):
    """Rate a completed order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order is completed
    if order.status != 'completed':
        messages.error(request, 'You can only rate completed orders.')
        return redirect('user_profile')
    
    # Check if already rated
    if hasattr(order, 'rating'):
        messages.info(request, 'You have already rated this order.')
        return redirect('user_profile')
    
    if request.method == 'POST':
        try:
            # Get common ratings
            product_rating = int(request.POST.get('product_rating'))
            product_comment = request.POST.get('product_comment', '').strip()
            service_rating = int(request.POST.get('service_rating'))
            service_comment = request.POST.get('service_comment', '').strip()
            overall_comment = request.POST.get('overall_comment', '').strip()
            
            # Validate ratings
            if not (1 <= product_rating <= 5) or not (1 <= service_rating <= 5):
                messages.error(request, 'Ratings must be between 1 and 5.')
                return redirect('rate_order', order_id=order_id)
            
            # Create rating object
            rating = Rating(
                order=order,
                user=request.user,
                product_rating=product_rating,
                product_comment=product_comment,
                service_rating=service_rating,
                service_comment=service_comment,
                overall_comment=overall_comment
            )
            
            # Get delivery-specific or pickup-specific ratings
            if order.delivery:
                delivery_rating = int(request.POST.get('delivery_rating'))
                delivery_comment = request.POST.get('delivery_comment', '').strip()
                
                if not (1 <= delivery_rating <= 5):
                    messages.error(request, 'Delivery rating must be between 1 and 5.')
                    return redirect('rate_order', order_id=order_id)
                
                rating.delivery_rating = delivery_rating
                rating.delivery_comment = delivery_comment
            else:
                pickup_speed_rating = int(request.POST.get('pickup_speed_rating'))
                
                if not (1 <= pickup_speed_rating <= 5):
                    messages.error(request, 'Pickup speed rating must be between 1 and 5.')
                    return redirect('rate_order', order_id=order_id)
                
                rating.pickup_speed_rating = pickup_speed_rating
            
            rating.save()
            
            # Create notification for admin
            admin_users = User.objects.filter(is_staff=True)
            for admin in admin_users:
                Notification.objects.create(
                    type='feedback',
                    message=f'{request.user.get_full_name() or request.user.username} rated Order #{order.id} with {rating.get_average_rating():.1f}/5 stars',
                    user=admin,
                    order=order
                )
            
            # Redirect with success parameter to show popup
            from django.urls import reverse
            return redirect(reverse('user_profile') + '?rating_submitted=true')
            
        except (ValueError, KeyError) as e:
            messages.error(request, 'Invalid rating data. Please try again.')
            return redirect('rate_order', order_id=order_id)
    
    context = {
        'order': order,
    }
    
    # Use different templates for pickup and delivery
    if order.delivery:
        return render(request, 'kakanin/rate_order_delivery.html', context)
    else:
        return render(request, 'kakanin/rate_order_pickup.html', context)
