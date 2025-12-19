from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Reset admin password'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the admin account')
        parser.add_argument('password', type=str, help='New password')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        
        try:
            user = User.objects.get(username=username)
            
            if not user.is_superuser:
                self.stdout.write(
                    self.style.WARNING(f'Warning: User "{username}" is not a superuser')
                )
            
            user.set_password(password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Password successfully reset for user "{username}"')
            )
            self.stdout.write(
                self.style.SUCCESS(f'You can now login with:')
            )
            self.stdout.write(f'  Username: {username}')
            self.stdout.write(f'  Password: {password}')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'✗ User "{username}" does not exist')
            )
