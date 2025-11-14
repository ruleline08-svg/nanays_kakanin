"""
Script to clean up old notifications from the database
Run this once to remove notifications created before the signal system
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nanays_kakanin.settings')
django.setup()

from kakanin.models import Notification

def clean_old_notifications():
    """Delete all existing notifications to start fresh with signal-based system"""
    
    # Count existing notifications
    total_count = Notification.objects.count()
    admin_count = Notification.objects.filter(user__isnull=True).count()
    user_count = Notification.objects.filter(user__isnull=False).count()
    
    print(f"Found {total_count} total notifications:")
    print(f"  - {admin_count} admin notifications")
    print(f"  - {user_count} user notifications")
    
    # Ask for confirmation
    response = input("\nDo you want to delete all old notifications? (yes/no): ")
    
    if response.lower() == 'yes':
        # Delete all notifications
        deleted_count = Notification.objects.all().delete()[0]
        print(f"\n✅ Deleted {deleted_count} notifications successfully!")
        print("The signal system will now create new notifications automatically.")
    else:
        print("\n❌ Cleanup cancelled. No notifications were deleted.")

if __name__ == '__main__':
    clean_old_notifications()
