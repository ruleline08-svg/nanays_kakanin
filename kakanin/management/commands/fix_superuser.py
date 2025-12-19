from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Fix superuser accounts by ensuring is_staff flag is set'

    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superuser accounts found.'))
            return
        
        fixed_count = 0
        for user in superusers:
            if not user.is_staff:
                user.is_staff = True
                user.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed user "{user.username}" - set is_staff=True')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'User "{user.username}" is already correctly configured')
                )
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nFixed {fixed_count} superuser account(s).')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nAll superuser accounts are correctly configured.')
            )
