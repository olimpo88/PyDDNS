from django.conf import settings
from django.contrib.auth import logout as djlogout
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse

from common.twofactor import has_2fa, is_forced_for

# Views a not-yet-enrolled admin must still reach: the enrolment pages
# themselves, the sign-in/out flow and the language switch.
EXEMPT_VIEWS = frozenset({
    'common:login', 'common:dologin', 'common:verify2fa', 'common:logout',
    'common:twofactor', 'common:twofactor_setup', 'common:twofactor_codes',
    'common:twofactor_disable', 'common:twofactor_regenerate',
    'set_language',
})


class TwoFactorMiddleware:
    """Enforce the second factor for authenticated sessions.

    Must sit after ``AuthenticationMiddleware`` and ``OTPMiddleware``.

    * A user who owns a 2FA device but whose session is not verified is
      signed out (this blocks any login path that skipped the code step).
    * With ADMIN_FORCE_2FA=1, staff without a device are sent to enrol.
    * Impersonated sessions are skipped: they are only created by a
      superuser who was already verified (see impersonate()).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not request.session.get('_impersonator_id'):
            if has_2fa(user):
                if not user.is_verified():
                    djlogout(request)
                    return redirect(settings.LOGIN_URL)
            elif is_forced_for(user) and not self._exempt(request):
                return redirect(reverse('common:twofactor_setup'))
        return self.get_response(request)

    @staticmethod
    def _exempt(request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return True  # nothing to protect (static files, 404s)
        return match.view_name in EXEMPT_VIEWS
