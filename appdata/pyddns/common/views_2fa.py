"""Self-service two-factor management: enrol, disable, regenerate codes."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django_otp import login as otp_login

from common import twofactor
from common.models import Activity_log
from common.utils import get_client_ip


def _log(request, action, result):
    Activity_log(
        action=action,
        xforward=get_client_ip(request),
        user_affected=request.user.get_username(),
        result=result,
    ).save()


def _impersonating(request):
    return bool(request.session.get('_impersonator_id'))


def self_service(view):
    """Login required, and never while acting as another user: an admin
    impersonating someone must not be able to enrol or strip their 2FA."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if _impersonating(request):
            return redirect('main')
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    wrapper.__doc__ = view.__doc__
    return wrapper


def _status_context(request, **extra):
    user = request.user
    ctx = {
        'enabled': twofactor.has_2fa(user),
        'forced': twofactor.is_forced_for(user),
        'codes_left': twofactor.backup_codes_left(user),
    }
    ctx.update(extra)
    return ctx


@self_service
def index(request):
    if twofactor.is_forced_for(request.user):
        # No settings page for forced admins: enrol, then back to the app.
        return redirect('main' if twofactor.has_2fa(request.user) else 'common:twofactor_setup')
    return render(request, 'twofactor/index.html', _status_context(request))


@self_service
@require_http_methods(['GET', 'POST'])
def setup(request):
    user = request.user
    if twofactor.has_2fa(user):
        return redirect('common:twofactor')
    device = twofactor.pending_totp_device(user)
    error = ''
    if request.method == 'POST':
        token = twofactor.normalize_token(request.POST.get('token', ''))
        if token and device.verify_token(token):
            twofactor.confirm_totp_device(device)
            # They just proved they hold the device: count this session as verified.
            otp_login(request, device)
            request.session[twofactor.NEW_CODES_KEY] = twofactor.generate_backup_codes(user)
            request.session[twofactor.ENROLLED_KEY] = True
            _log(request, '2FA_ENABLE', 'Two-factor authentication enabled')
            return redirect('common:twofactor_codes')
        error = _('Invalid code.')
    return render(request, 'twofactor/setup.html', {
        'qr_svg': twofactor.qr_svg(device.config_url),
        'secret': _spaced_secret(device),
        'forced': twofactor.is_forced_for(user),
        'error': error,
    })


def _spaced_secret(device):
    """Base32 secret in groups of four, for typing into an authenticator."""
    from base64 import b32encode
    raw = b32encode(device.bin_key).decode('ascii').rstrip('=')
    return ' '.join(raw[i:i + 4] for i in range(0, len(raw), 4))


@self_service
def codes(request):
    """Show freshly generated backup codes exactly once."""
    new_codes = request.session.pop(twofactor.NEW_CODES_KEY, None)
    if not new_codes:
        return redirect('common:twofactor')
    just_enrolled = request.session.pop(twofactor.ENROLLED_KEY, False)
    return render(request, 'twofactor/codes.html', {
        'codes': new_codes,
        'just_enrolled': just_enrolled,
        'continue_url': reverse('main') if just_enrolled else reverse('common:twofactor'),
    })


@self_service
@require_http_methods(['POST'])
def regenerate(request):
    user = request.user
    if twofactor.is_forced_for(user):
        return redirect('main')
    if not twofactor.has_2fa(user):
        return redirect('common:twofactor')
    if not user.check_password(request.POST.get('password', '')):
        return render(request, 'twofactor/index.html',
                      _status_context(request, error=_('Wrong password.')), status=403)
    request.session[twofactor.NEW_CODES_KEY] = twofactor.generate_backup_codes(user)
    _log(request, '2FA_BACKUP_CODES', 'Backup codes regenerated')
    return redirect('common:twofactor_codes')


@self_service
@require_http_methods(['POST'])
def disable(request):
    user = request.user
    if not twofactor.has_2fa(user):
        return redirect('common:twofactor')
    if twofactor.is_forced_for(user):
        return render(request, 'twofactor/index.html',
                      _status_context(request, error=_('Two-factor authentication is required for administrators and cannot be disabled.')),
                      status=403)
    if not user.check_password(request.POST.get('password', '')):
        return render(request, 'twofactor/index.html',
                      _status_context(request, error=_('Wrong password.')), status=403)
    twofactor.remove_2fa(user)
    _log(request, '2FA_DISABLE', 'Two-factor authentication disabled')
    return redirect('common:twofactor')
