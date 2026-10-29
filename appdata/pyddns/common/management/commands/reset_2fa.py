from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from common import twofactor
from common.models import Activity_log


class Command(BaseCommand):
    help = (
        "Remove every two-factor device (authenticator + backup codes) of a "
        "user. Recovery path for a lost phone. With ADMIN_FORCE_2FA=1 an admin "
        "is asked to enrol again at their next sign-in."
    )

    def add_arguments(self, parser):
        parser.add_argument('username')

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: options['username']})
        except User.DoesNotExist:
            raise CommandError('User %r does not exist.' % options['username'])
        removed = twofactor.remove_2fa(user)
        Activity_log(
            action='2FA_RESET',
            user_affected=user.get_username(),
            result='Reset from the command line (%d device(s) removed)' % removed,
        ).save()
        self.stdout.write(self.style.SUCCESS(
            '%s: %d device(s) removed.' % (user.get_username(), removed)
        ))
