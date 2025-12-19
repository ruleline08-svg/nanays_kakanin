from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class Command(BaseCommand):
    help = 'Check user account details and test authentication'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to check')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            
            self.stdout.write(self.style.SUCCESS(f'\n=== User Details for "{username}" ==='))
            self.stdout.write(f'ID: {user.id}')
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'First Name: {user.first_name}')
            self.stdout.write(f'Last Name: {user.last_name}')
            self.stdout.write(f'is_active: {user.is_active}')
            self.stdout.write(f'is_staff: {user.is_staff}')
            self.stdout.write(f'is_superuser: {user.is_superuser}')
            self.stdout.write(f'Date joined: {user.date_joined}')
            self.stdout.write(f'Last login: {user.last_login}')
            self.stdout.write(f'Password hash: {user.password[:50]}...')
            
            if not user.is_active:
                self.stdout.write(self.style.ERROR('\n⚠️  User is NOT active!'))
            
            if user.is_superuser and not user.is_staff:
                self.stdout.write(self.style.ERROR('\n⚠️  Superuser without is_staff flag!'))
            
            self.stdout.write(self.style.SUCCESS('\n✓ User account exists and is properly configured'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'\n✗ User "{username}" does not exist'))
