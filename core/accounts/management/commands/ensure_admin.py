import os

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = 'Grants superuser access to the account selected by ADMIN_USERNAME.'

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', '').strip()
        if not username:
            self.stdout.write('ADMIN_USERNAME is not set; skipping admin bootstrap.')
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(
                f'No user exists with username "{username}". Create that account first.'
            ) from exc

        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=('role', 'is_staff', 'is_superuser'))
        self.stdout.write(self.style.SUCCESS(f'Admin access granted to {username}.'))
