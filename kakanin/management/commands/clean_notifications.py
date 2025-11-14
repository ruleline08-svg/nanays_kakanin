"""
Django management command to clean up old notifications
Usage: python manage.py clean_notifications
"""
from django.core.management.base import BaseCommand
from kakanin.models import Notification


class Command(BaseCommand):
    help = 'Clean up old notifications from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete all notifications',
        )
        parser.add_argument(
            '--read',
            action='store_true',
            help='Delete only read notifications',
        )
        parser.add_argument(
            '--old',
            type=int,
            help='Delete notifications older than X days',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Delete all notifications
            count = Notification.objects.count()
            self.stdout.write(f"Found {count} notifications")
            
            confirm = input("Delete all notifications? (yes/no): ")
            if confirm.lower() == 'yes':
                deleted = Notification.objects.all().delete()[0]
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted} notifications'))
            else:
                self.stdout.write(self.style.WARNING('❌ Cancelled'))
        
        elif options['read']:
            # Delete only read notifications
            count = Notification.objects.filter(read=True).count()
            self.stdout.write(f"Found {count} read notifications")
            
            confirm = input("Delete read notifications? (yes/no): ")
            if confirm.lower() == 'yes':
                deleted = Notification.objects.filter(read=True).delete()[0]
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted} read notifications'))
            else:
                self.stdout.write(self.style.WARNING('❌ Cancelled'))
        
        elif options['old']:
            # Delete notifications older than X days
            from django.utils import timezone
            from datetime import timedelta
            
            days = options['old']
            cutoff_date = timezone.now() - timedelta(days=days)
            count = Notification.objects.filter(created_at__lt=cutoff_date).count()
            
            self.stdout.write(f"Found {count} notifications older than {days} days")
            
            confirm = input(f"Delete notifications older than {days} days? (yes/no): ")
            if confirm.lower() == 'yes':
                deleted = Notification.objects.filter(created_at__lt=cutoff_date).delete()[0]
                self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted} old notifications'))
            else:
                self.stdout.write(self.style.WARNING('❌ Cancelled'))
        
        else:
            # Show statistics
            total = Notification.objects.count()
            admin = Notification.objects.filter(user__isnull=True).count()
            user = Notification.objects.filter(user__isnull=False).count()
            read = Notification.objects.filter(read=True).count()
            unread = Notification.objects.filter(read=False).count()
            
            self.stdout.write("\n📊 Notification Statistics:")
            self.stdout.write(f"  Total: {total}")
            self.stdout.write(f"  Admin notifications: {admin}")
            self.stdout.write(f"  User notifications: {user}")
            self.stdout.write(f"  Read: {read}")
            self.stdout.write(f"  Unread: {unread}")
            self.stdout.write("\nUsage:")
            self.stdout.write("  python manage.py clean_notifications --all     # Delete all")
            self.stdout.write("  python manage.py clean_notifications --read    # Delete read only")
            self.stdout.write("  python manage.py clean_notifications --old 30  # Delete older than 30 days")
