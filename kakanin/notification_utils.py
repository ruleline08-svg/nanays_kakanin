"""
Utility functions for notification management
"""
from .models import Notification


def create_admin_notification(notification_type, message, order=None, reservation=None):
    """
    Create a notification for admin users
    Admin notifications have user=None
    """
    return Notification.objects.create(
        type=notification_type,
        message=message,
        user=None,  # Admin notification
        order=order,
        reservation=reservation
    )


def create_user_notification(user, notification_type, message, order=None, reservation=None):
    """
    Create a notification for a specific user
    """
    return Notification.objects.create(
        type=notification_type,
        message=message,
        user=user,
        order=order,
        reservation=reservation
    )


def mark_notification_as_read(notification_id, user):
    """
    Mark a notification as read
    Ensures the notification belongs to the user (or is an admin notification for staff)
    """
    try:
        if user.is_staff:
            # Admin can mark admin notifications (user=None) as read
            notification = Notification.objects.get(id=notification_id, user__isnull=True)
        else:
            # Regular user can only mark their own notifications as read
            notification = Notification.objects.get(id=notification_id, user=user)
        
        notification.read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False


def mark_all_notifications_as_read(user):
    """
    Mark all notifications as read for a user
    """
    if user.is_staff:
        # Mark all admin notifications as read
        Notification.objects.filter(user__isnull=True, read=False).update(read=True)
    else:
        # Mark all user's notifications as read
        Notification.objects.filter(user=user, read=False).update(read=True)
    
    return True


def get_user_notifications(user, unread_only=False, limit=None):
    """
    Get notifications for a specific user
    """
    queryset = Notification.objects.filter(user=user)
    
    if unread_only:
        queryset = queryset.filter(read=False)
    
    queryset = queryset.order_by('-created_at')
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def get_admin_notifications(unread_only=False, limit=None):
    """
    Get admin notifications (user=None)
    """
    queryset = Notification.objects.filter(user__isnull=True)
    
    if unread_only:
        queryset = queryset.filter(read=False)
    
    queryset = queryset.order_by('-created_at')
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def delete_old_notifications(days=30):
    """
    Delete read notifications older than specified days
    Helps keep the database clean
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count = Notification.objects.filter(
        read=True,
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return deleted_count
