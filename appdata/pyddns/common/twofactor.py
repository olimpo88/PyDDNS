"""Two-factor helpers shared by views, middleware and the admin site.

Built on django-otp: a TOTP device (authenticator app) plus a static device
holding one-time backup codes. A user "has 2FA" when they own a *confirmed*
device of either kind.
"""
import io
import re

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.utils import timezone
from django_otp import devices_for_user, user_has_device
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

BACKUP_CODE_COUNT = 10
TOTP_DEVICE_NAME = 'default'
STATIC_DEVICE_NAME = 'backup'

# Session keys
PENDING_KEY = '_2fa_pending'        # password OK, waiting for the code
NEW_CODES_KEY = '_2fa_new_codes'    # backup codes to show once
ENROLLED_KEY = '_2fa_just_enrolled'  # codes page leads on to the app, not back to settings
PENDING_TTL_SECONDS = 300
PENDING_MAX_ATTEMPTS = 5


def has_2fa(user):
    """True if the user has a confirmed second factor."""
    return bool(user and user.is_authenticated and user_has_device(user))


def is_forced_for(user):
    """ADMIN_FORCE_2FA applies to staff and superusers."""
    return bool(
        settings.ADMIN_FORCE_2FA
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


def requires_second_factor(user):
    return has_2fa(user) or is_forced_for(user)


def normalize_token(raw):
    """Authenticator codes are digits; backup codes are lowercase. Tolerate
    spaces/dashes people add when typing them."""
    return ''.join(ch for ch in (raw or '') if ch.isalnum()).lower()


def pending_totp_device(user):
    """The not-yet-confirmed TOTP device being enrolled (kept stable across
    page reloads so the QR on screen keeps matching)."""
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name=TOTP_DEVICE_NAME, confirmed=False)
    return device


def confirm_totp_device(device):
    device.confirmed = True
    device.save(update_fields=['confirmed'])


def qr_svg(data):
    """Render ``data`` as an inline SVG QR code (no image libraries needed)."""
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode('utf-8')
    # Drop the XML prolog and the fixed mm size so CSS can scale it.
    svg = re.sub(r'^<\?xml[^>]*\?>\s*', '', svg)
    return re.sub(r'<svg ([^>]*?)\s+width="[^"]*"\s+height="[^"]*"', r'<svg \1 style="width:100%;height:100%"', svg, count=1)


def generate_backup_codes(user, count=BACKUP_CODE_COUNT):
    """Replace the user's backup codes with ``count`` fresh ones and return
    them. Codes are only ever shown once."""
    device, _ = StaticDevice.objects.get_or_create(
        user=user, name=STATIC_DEVICE_NAME, defaults={'confirmed': True},
    )
    if not device.confirmed:
        device.confirmed = True
        device.save(update_fields=['confirmed'])
    device.token_set.all().delete()
    codes = []
    for _i in range(count):
        token = StaticToken.random_token()
        device.token_set.create(token=token)
        codes.append(token)
    return codes


def backup_codes_left(user):
    device = StaticDevice.objects.filter(user=user, name=STATIC_DEVICE_NAME).first()
    return device.token_set.count() if device else 0


def remove_2fa(user):
    """Delete every device of the user. Returns how many were removed."""
    removed = 0
    for device in list(devices_for_user(user, confirmed=None)):
        device.delete()
        removed += 1
    return removed


def pending_session_valid(pending):
    return bool(pending) and (timezone.now().timestamp() - pending.get('ts', 0)) <= PENDING_TTL_SECONDS


def user_has_confirmed_device(user):
    """Like has_2fa() but for a user who has not logged in yet."""
    return bool(user and user_has_device(user))
