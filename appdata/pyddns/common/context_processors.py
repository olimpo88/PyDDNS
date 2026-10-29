"""Template context processors that expose selected settings to all templates."""
from django.conf import settings

from common import twofactor


def site_context(request):
    """Expose DNS-related settings (and other safe values) to every template."""
    impersonator = None
    impersonator_id = None
    if hasattr(request, 'session'):
        impersonator_id = request.session.get('_impersonator_id')
    if impersonator_id:
        from django.contrib.auth import get_user_model
        try:
            impersonator = get_user_model().objects.get(id=impersonator_id)
        except get_user_model().DoesNotExist:
            impersonator = None

    user = getattr(request, 'user', None)
    return {
        # Admins forced to use 2FA have no settings page: enrol, then carry on.
        'TWOFA_FORCED': bool(user and user.is_authenticated and twofactor.is_forced_for(user)),
        'PYDDNS_VERSION': getattr(settings, 'PYDDNS_VERSION', ''),
        'DNS_DOMAIN': getattr(settings, 'DNS_DOMAIN', None) or '',
        'OWN_ADMIN': getattr(settings, 'OWN_ADMIN', '0') == '1',
        'LANGUAGE_LOCKED': getattr(settings, 'LANGUAGE_LOCKED', False),
        'IS_IMPERSONATING': bool(impersonator),
        'IMPERSONATOR': impersonator,
        'ALLOW_PASSWORD_RESET': getattr(settings, 'ALLOW_PASSWORD_RESET', True),
    }
