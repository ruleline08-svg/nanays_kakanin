from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from kakanin.models import Notification


class Command(BaseCommand):
    help = 'Convert existing admin notifications to use user=None instead of specific admin users'

    def handle(self, *args, **options):
        # Get all admin users
        admin_users = User.objects.filter(is_superuser=True)
        admin_user_ids = list(admin_users.values_list('id', flat=True))
        
        if not admin_user_ids:
            self.stdout.write(self.style.WARNING('No admin users found.'))
            return
        
        # Find notifications that were sent to admin users
        # These are notifications about user actions (orders, reservations, etc.)
        admin_notifications = Notification.objects.filter(
            user_id__in=admin_user_ids
        ).exclude(
            type__in=[
                'order_confirmed',
                'ready_for_pickup', 
                'out_for_delivery',
                'order_completed',
                'payment_approved',
                'payment_rejected',
                'reservation_confirmed',
                'reservation_rejected',
                'reservation_completed'
            ]
        )
        
        count = admin_notifications.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No admin notifications to convert.'))
            return
        
        # Group by message to avoid duplicates
        # (old system created one notification per admin)
        seen_messages = set()
        notifications_to_keep = []
        notifications_to_delete = []
        
        for notif in admin_notifications.order_by('created_at'):
            key = (notif.message, notif.type, notif.order_id, notif.reservation_id)
            if key not in seen_messages:
                seen_messages.add(key)
                notifications_to_keep.append(notif.id)
            else:
                notifications_to_delete.append(notif.id)
        
        # Delete duplicate notifications
        if notifications_to_delete:
            deleted_count = Notification.objects.filter(id__in=notifications_to_delete).delete()[0]
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count} duplicate admin notifications.'))
        
        # Update remaining notifications to have user=None
        updated_count = Notification.objects.filter(id__in=notifications_to_keep).update(user=None)
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully converted {updated_count} admin notifications to use user=None.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total admin notifications now: {Notification.objects.filter(user__isnull=True).count()}'
        ))
