from urllib.parse import quote

from django.contrib import admin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.conf import settings

from common.twofactor import requires_second_factor


class SecureAdminSite(admin.AdminSite):
    """Django admin that honours two-factor authentication.

    * The password form of ``/admin/login/`` is never used: that would be a
      way to log in without the second factor. Anonymous visitors are sent
      to the app login (which handles the TOTP step) and come back here.
    * A user who must use a second factor (has a device, or is staff while
      ADMIN_FORCE_2FA=1) is only let in once their session is verified.
      Everybody else keeps today's behaviour.
    """

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if requires_second_factor(request.user):
            return request.user.is_verified()
        return True

    def login(self, request, extra_context=None):
        if request.user.is_authenticated:
            # Logged in but not allowed here (not staff, or not verified):
            # bouncing to the login page again would loop.
            return HttpResponseForbidden('Forbidden')
        target = '%s?next=%s' % (settings.LOGIN_URL, quote(request.get_full_path(), safe='/'))
        return HttpResponseRedirect(target)
