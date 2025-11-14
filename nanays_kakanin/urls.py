from django.contrib import admin
from django.urls import path, include
from kakanin import views
from kakanin import reservation_views
from django.conf import settings
from django.conf.urls.static import static
 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name="home"),
    path('about/', views.about, name="about"),
    path('contact/', views.contact, name="contact"),
    path('signup/', views.signup_view, name="signup"),
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),
    path('shop/', views.shop_view, name="shop"), 
    path("guest/", views.index, name='index'),
    path("user/", views.index_user, name="index_user"),
    path("user/shop/", views.shop_user, name="shop_user"),

    # New cartless preorder flow

    path("profile/", views.user_profile, name="user_profile"),
    path("notifications/", views.user_notifications, name="user_notifications"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),

    
    # Admin URLs
   path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
   path("admin-notifications/", views.admin_notifications, name="admin_notifications"),
   path("admin-notifications/<int:notification_id>/read/", views.admin_mark_notification_read, name="admin_mark_notification_read"),
   path("admin-products/", views.admin_products, name="admin_products"),
   path("admin-products/create/", views.admin_product_create, name="admin_product_create"),
   path("admin-products/<int:product_id>/edit/", views.admin_product_edit, name="admin_product_edit"),
   path("admin-products/<int:product_id>/delete/", views.admin_product_delete, name="admin_product_delete"),
   path("admin-content/", views.admin_content, name="admin_content"),
   path("admin-about/edit/", views.admin_about_edit, name="admin_about_edit"),
   path("admin-about/delete/", views.admin_about_delete, name="admin_about_delete"),
   path("admin-contact/edit/", views.admin_contact_edit, name="admin_contact_edit"),
   path("admin-contact/delete/", views.admin_contact_delete, name="admin_contact_delete"),
   path("admin-users/", views.admin_users, name="admin_users"),
   path("admin-user-create/", views.admin_user_create, name="admin_user_create"),
   path("admin-user-edit/<int:user_id>/", views.admin_user_edit, name="admin_user_edit"),
   path("admin-user-toggle/<int:user_id>/", views.admin_user_toggle, name="admin_user_toggle"),
   path("admin-user-delete/<int:user_id>/", views.admin_user_delete, name="admin_user_delete"),
 
 
   # Admin Reservations
 
    # Admin Feedback
    path("admin-feedback/", views.admin_feedback_list, name="admin_feedback"),
    path("admin-feedback/delete/<int:feedback_id>/", views.admin_feedback_delete, name="admin_feedback_delete"),
    
    # Admin Ratings
    path("admin-ratings/delete/", views.admin_ratings_delete, name="admin_ratings_delete"),
    
    # Messaging
    path("messages/", views.messages_inbox, name="messages_inbox"),
    path("messages/thread/<int:user_id>/", views.message_thread, name="message_thread"),
    path("messages/send/", views.send_message, name="send_message"),
    path("messages/<int:message_id>/edit/", views.edit_message, name="edit_message"),
    path("messages/<int:message_id>/unsend/", views.unsend_message, name="unsend_message"),
    path("messages/<int:message_id>/reply/", views.reply_message, name="reply_message"),
 
    # Feedback
    path("feedback/submit/", views.submit_feedback, name="submit_feedback"),
    
    # Cart - Unified
    path("cart/", views.unified_cart, name="cart"),
    path("cart/", views.unified_cart, name="view_cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="cart_add"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="cart_remove"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    path("checkout/", views.checkout_cart, name="checkout"),
    path("cart/checkout/", views.checkout_cart, name="checkout_cart"),
    
    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("orders/my/", views.order_list, name="my_orders"),  # Alias for user orders
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/create/<int:product_id>/", views.create_order, name="create_order"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:order_id>/rate/", views.rate_order, name="rate_order"),
    
    # Reservations
    path("reservations/", views.reservation_list, name="reservation_list"),
    path("reservations/<int:reservation_id>/cancel/", views.cancel_reservation, name="cancel_reservation"),
    
    # Admin Orders
    path("admin/orders/", views.admin_orders, name="admin_orders_view"),  # Alias
    path("admin-orders/", views.admin_orders, name="admin_orders"),
    path("admin/order/<int:order_id>/", views.admin_order_detail, name="admin_order_detail_view"),  # Alias
    path("admin-orders/<int:order_id>/", views.admin_order_detail, name="admin_order_detail"),
    path("admin-orders/<int:order_id>/delete/", views.admin_order_delete, name="admin_order_delete"),
    path("admin-orders/bulk-delete/", views.admin_bulk_delete_orders, name="admin_bulk_delete_orders"),
    
    # Reservations - User views
    path("reservation/shop/", views.reservation_shop, name="reservation_shop"),
    path("reservation/create/<int:product_id>/", views.reservation_create, name="reservation_create"),
    path("reservations/my/", views.my_reservations, name="my_reservations"),
    
    # Reservation Cart
    path("reservation/cart/add/<int:product_id>/", views.add_to_reservation_cart, name="add_to_reservation_cart"),
    path("reservation/cart/", views.reservation_cart, name="reservation_cart"),
    path("reservation/cart/remove/<int:item_id>/", views.remove_from_reservation_cart, name="remove_from_reservation_cart"),
    path("reservation/cart/update/<int:item_id>/", views.update_reservation_cart, name="update_reservation_cart"),
    path("reservation/submit/", reservation_views.submit_reservation, name="submit_reservation"),
    path("reservation/<int:reservation_id>/payment/", reservation_views.reservation_payment, name="reservation_payment"),
    path("reservation/checkout/", views.reservation_checkout, name="reservation_checkout"),
    
    # Reservations - Admin views
    path("admin-reservations/", reservation_views.admin_reservations, name="admin_reservations"),
    path("admin-reservations/<int:reservation_id>/", reservation_views.admin_reservation_detail, name="admin_reservation_detail"),
    path("admin-reservations/<int:reservation_id>/confirm/", reservation_views.admin_reservation_confirm, name="admin_reservation_confirm"),
    path("admin-reservations/<int:reservation_id>/reject/", reservation_views.admin_reservation_reject, name="admin_reservation_reject"),
    path("admin-reservations/<int:reservation_id>/complete/", reservation_views.admin_reservation_complete, name="admin_reservation_complete"),
    path("admin-reservations/bulk-delete/", reservation_views.admin_bulk_delete_reservations, name="admin_bulk_delete_reservations"),

    # Debug
    path("storage-debug/", views.storage_debug, name="storage_debug"),
]
 
# Serve static + media in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
