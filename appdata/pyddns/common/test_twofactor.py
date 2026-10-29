import json

import pytest
from django.core.management import call_command
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from common import twofactor
from common.models import Activity_log

pytestmark = pytest.mark.django_db


# ---------- helpers ----------

def totp_code(device):
    return '%06d' % TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()


def enrol(user):
    """Give ``user`` a confirmed TOTP device plus backup codes."""
    device = TOTPDevice.objects.create(user=user, name='default', confirmed=True)
    codes = twofactor.generate_backup_codes(user)
    return device, codes


def password_step(client, username, password, **extra):
    client.get(reverse('common:login'))  # primes the test cookie
    response = client.post(reverse('common:dologin'),
                           dict(username=username, password=password, **extra))
    return json.loads(response.content)


def code_step(client, token):
    response = client.post(reverse('common:verify2fa'), {'token': token})
    return json.loads(response.content)


def login_with_2fa(client, user, password):
    device = TOTPDevice.objects.get(user=user, confirmed=True)
    assert password_step(client, user.username, password)['two_factor'] is True
    data = code_step(client, totp_code(device))
    assert data['success'] is True
    return data


def is_logged_in(client):
    return '_auth_user_id' in client.session


# ---------- login: second step ----------

def test_password_step_does_not_log_in_when_2fa_enabled(client, regular_user):
    enrol(regular_user)
    data = password_step(client, 'bob', 'bob-pass')
    assert data['success'] is False
    assert data['two_factor'] is True
    assert not is_logged_in(client)
    assert client.get(reverse('main')).status_code == 302


def test_password_step_pending_is_not_counted_as_failure(client, regular_user):
    enrol(regular_user)
    for _i in range(6):
        assert password_step(client, 'bob', 'bob-pass')['two_factor'] is True
    assert not Activity_log.objects.filter(action='DOLOGIN', result__startswith='False').exists()


def test_wrong_password_never_reaches_second_step(client, regular_user):
    enrol(regular_user)
    data = password_step(client, 'bob', 'nope')
    assert data['success'] is False
    assert 'two_factor' not in data


def test_valid_totp_completes_login_and_verifies_session(client, regular_user):
    enrol(regular_user)
    data = login_with_2fa(client, regular_user, 'bob-pass')
    assert data['redirect'] == '/main/'
    assert is_logged_in(client)
    assert client.get(reverse('main')).status_code == 200


def test_wrong_code_does_not_log_in(client, regular_user):
    enrol(regular_user)
    password_step(client, 'bob', 'bob-pass')
    data = code_step(client, '000000')
    assert data['success'] is False
    assert not is_logged_in(client)


def test_five_wrong_codes_force_restart_from_password(client, regular_user):
    device, _codes = enrol(regular_user)
    password_step(client, 'bob', 'bob-pass')
    last = None
    for _i in range(twofactor.PENDING_MAX_ATTEMPTS):
        last = code_step(client, '000000')
    assert last['restart'] is True
    # The correct code no longer works without redoing the password step.
    data = code_step(client, totp_code(device))
    assert data['success'] is False
    assert data['restart'] is True


def test_wrong_code_is_throttled_even_for_the_right_code(client, regular_user):
    device, _codes = enrol(regular_user)
    password_step(client, 'bob', 'bob-pass')
    code_step(client, '000000')
    # Immediately retrying with the valid code is refused by django-otp's back-off.
    assert code_step(client, totp_code(device))['success'] is False


def test_code_step_without_pending_password(client, regular_user):
    device, _codes = enrol(regular_user)
    data = code_step(client, totp_code(device))
    assert data['success'] is False
    assert data['restart'] is True
    assert not is_logged_in(client)


def test_code_step_rejects_get(client):
    assert client.get(reverse('common:verify2fa')).status_code == 405


def test_backup_code_works_once(client, regular_user):
    _device, codes = enrol(regular_user)
    password_step(client, 'bob', 'bob-pass')
    assert code_step(client, codes[0])['success'] is True
    client.get(reverse('common:logout'))
    password_step(client, 'bob', 'bob-pass')
    assert code_step(client, codes[0])['success'] is False
    assert twofactor.backup_codes_left(regular_user) == len(codes) - 1


def test_backup_code_tolerates_case_and_spaces(client, regular_user):
    _device, codes = enrol(regular_user)
    password_step(client, 'bob', 'bob-pass')
    assert code_step(client, ' %s ' % codes[1].upper())['success'] is True


def test_login_honours_safe_next_only(client, regular_user):
    assert password_step(client, 'bob', 'bob-pass', next='/en/users/')['redirect'] == '/en/users/'
    client.get(reverse('common:logout'))
    assert password_step(client, 'bob', 'bob-pass', next='https://evil.example/')['redirect'] == '/main/'


def test_next_survives_the_code_step(client, regular_user):
    device, _codes = enrol(regular_user)
    password_step(client, 'bob', 'bob-pass', next='/en/users/')
    assert code_step(client, totp_code(device))['redirect'] == '/en/users/'


def test_users_without_2fa_log_in_as_before(client, regular_user):
    data = password_step(client, 'bob', 'bob-pass')
    assert data['success'] is True
    assert 'two_factor' not in data


# ---------- enrolment / management ----------

def test_management_pages_require_login(client):
    for name in ('twofactor', 'twofactor_setup', 'twofactor_codes'):
        assert client.get(reverse('common:' + name)).status_code == 302


def test_enrol_flow(user_client, regular_user):
    response = user_client.get(reverse('common:twofactor_setup'))
    assert response.status_code == 200
    assert b'<svg' in response.content
    device = TOTPDevice.objects.get(user=regular_user, confirmed=False)

    bad = user_client.post(reverse('common:twofactor_setup'), {'token': '000000'})
    assert bad.status_code == 200
    assert not twofactor.has_2fa(regular_user)
    # django-otp throttles right after a wrong code; skip the back-off here
    # (test_wrong_code_is_throttled covers the behaviour itself).
    TOTPDevice.objects.filter(pk=device.pk).update(throttling_failure_count=0, throttling_failure_timestamp=None)

    ok = user_client.post(reverse('common:twofactor_setup'), {'token': totp_code(device)})
    assert ok.status_code == 302
    assert twofactor.has_2fa(regular_user)

    shown = user_client.get(reverse('common:twofactor_codes'))
    assert shown.status_code == 200
    for code in StaticDevice.objects.get(user=regular_user).token_set.values_list('token', flat=True):
        assert code.encode() in shown.content
    # After enrolling, the button leads on to the app instead of back to settings.
    assert f'href="{reverse("main")}"'.encode() in shown.content
    # Shown once only.
    assert user_client.get(reverse('common:twofactor_codes')).status_code == 302
    assert Activity_log.objects.filter(action='2FA_ENABLE', user_affected='bob').exists()


def test_setup_page_keeps_same_secret_on_reload(user_client, regular_user):
    user_client.get(reverse('common:twofactor_setup'))
    first = TOTPDevice.objects.get(user=regular_user).key
    user_client.get(reverse('common:twofactor_setup'))
    assert TOTPDevice.objects.get(user=regular_user).key == first


def test_setup_redirects_when_already_enabled(client, regular_user):
    enrol(regular_user)
    login_with_2fa(client, regular_user, 'bob-pass')
    assert client.get(reverse('common:twofactor_setup')).status_code == 302


def test_disable_requires_password(client, regular_user):
    enrol(regular_user)
    login_with_2fa(client, regular_user, 'bob-pass')
    response = client.post(reverse('common:twofactor_disable'), {'password': 'wrong'})
    assert response.status_code == 403
    assert twofactor.has_2fa(regular_user)

    response = client.post(reverse('common:twofactor_disable'), {'password': 'bob-pass'})
    assert response.status_code == 302
    assert not twofactor.has_2fa(regular_user)
    assert not TOTPDevice.objects.filter(user=regular_user).exists()
    assert not StaticDevice.objects.filter(user=regular_user).exists()


def test_regenerate_requires_password_and_replaces_codes(client, regular_user):
    _device, old_codes = enrol(regular_user)
    login_with_2fa(client, regular_user, 'bob-pass')
    assert client.post(reverse('common:twofactor_regenerate'), {'password': 'wrong'}).status_code == 403
    assert client.post(reverse('common:twofactor_regenerate'), {'password': 'bob-pass'}).status_code == 302
    new_codes = list(StaticDevice.objects.get(user=regular_user).token_set.values_list('token', flat=True))
    assert len(new_codes) == twofactor.BACKUP_CODE_COUNT
    assert not set(new_codes) & set(old_codes)


def test_index_page_renders_both_states(user_client):
    assert user_client.get(reverse('common:twofactor')).status_code == 200


# ---------- ADMIN_FORCE_2FA ----------

def test_force_off_leaves_existing_admins_alone(admin_client):
    assert admin_client.get(reverse('main')).status_code == 200
    assert admin_client.get(reverse('admin:index')).status_code == 200


def test_force_redirects_admin_without_device_to_enrol(settings, admin_client):
    settings.ADMIN_FORCE_2FA = True
    response = admin_client.get(reverse('main'))
    assert response.status_code == 302
    assert response['Location'] == reverse('common:twofactor_setup')


def test_force_leaves_enrolment_pages_reachable(settings, admin_client):
    settings.ADMIN_FORCE_2FA = True
    assert admin_client.get(reverse('common:twofactor_setup')).status_code == 200
    # Forced admins have no settings page: it just sends them on to enrol.
    response = admin_client.get(reverse('common:twofactor'))
    assert response.status_code == 302
    assert response['Location'] == reverse('common:twofactor_setup')
    assert admin_client.get(reverse('common:logout')).status_code == 302


def test_force_does_not_touch_regular_users(settings, user_client):
    settings.ADMIN_FORCE_2FA = True
    assert user_client.get(reverse('main')).status_code == 200


def test_force_enrolment_unlocks_the_app(settings, admin_client, admin_user):
    settings.ADMIN_FORCE_2FA = True
    admin_client.get(reverse('common:twofactor_setup'))
    device = TOTPDevice.objects.get(user=admin_user)
    admin_client.post(reverse('common:twofactor_setup'), {'token': totp_code(device)})
    assert admin_client.get(reverse('main')).status_code == 200
    assert admin_client.get(reverse('admin:index')).status_code == 200


def test_force_blocks_admin_from_disabling(settings, client, admin_user):
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    settings.ADMIN_FORCE_2FA = True
    response = client.post(reverse('common:twofactor_disable'), {'password': 'admin-pass'})
    assert response.status_code == 403
    assert twofactor.has_2fa(admin_user)


def test_force_hides_settings_page_once_enrolled(settings, client, admin_user):
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    settings.ADMIN_FORCE_2FA = True
    response = client.get(reverse('common:twofactor'))
    assert response.status_code == 302
    assert response['Location'] == reverse('main')
    response = client.post(reverse('common:twofactor_regenerate'), {'password': 'admin-pass'})
    assert response.status_code == 302
    assert response['Location'] == reverse('main')


def test_force_applies_to_staff_not_only_superusers(settings, client, regular_user):
    regular_user.is_staff = True
    regular_user.save()
    settings.ADMIN_FORCE_2FA = True
    client.force_login(regular_user)
    assert client.get(reverse('main')).status_code == 302


# ---------- admin resets another user's 2FA ----------

def test_admin_can_reset_another_users_2fa(client, admin_user, regular_user):
    enrol(regular_user)
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    response = client.post(reverse('reset_user_2fa'), {'id_user': regular_user.id})
    assert response.status_code == 200
    assert json.loads(response.content)['success'] is True
    assert not twofactor.has_2fa(regular_user)
    assert twofactor.has_2fa(admin_user)
    log = Activity_log.objects.get(action='2FA_RESET', user_affected='bob')
    assert 'admin' in log.result


def test_reset_lets_the_user_in_with_the_password_alone(client, admin_user, regular_user):
    enrol(regular_user)
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    client.post(reverse('reset_user_2fa'), {'id_user': regular_user.id})
    client.logout()
    data = password_step(client, 'bob', 'bob-pass')
    assert data['success'] is True
    assert not data.get('two_factor')


def test_admin_cannot_reset_their_own_2fa_here(client, admin_user):
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    response = client.post(reverse('reset_user_2fa'), {'id_user': admin_user.id})
    assert response.status_code == 403
    assert twofactor.has_2fa(admin_user)


def test_regular_user_cannot_reset_anyones_2fa(client, regular_user, other_user):
    enrol(other_user)
    enrol(regular_user)
    login_with_2fa(client, regular_user, 'bob-pass')
    response = client.post(reverse('reset_user_2fa'), {'id_user': other_user.id})
    assert response.status_code == 302
    assert twofactor.has_2fa(other_user)


def test_reset_requires_post_and_a_real_user(admin_client, regular_user):
    assert admin_client.get(reverse('reset_user_2fa')).status_code == 405
    assert admin_client.post(reverse('reset_user_2fa'), {'id_user': 99999}).status_code == 404
    assert admin_client.post(reverse('reset_user_2fa'), {'id_user': 'x'}).status_code == 404


def test_users_page_offers_reset_only_for_users_with_2fa(admin_client, regular_user, other_user):
    enrol(regular_user)
    html = admin_client.get(reverse('users')).content.decode()
    assert html.count('confirm2fa = {') == 1
    assert "name: 'bob'" in html


def test_edit_user_page_offers_reset_only_when_the_user_has_2fa(admin_client, regular_user):
    url = f'/add_user/{regular_user.id}'
    assert b'confirm2fa = true' not in admin_client.get(url, follow=True).content
    enrol(regular_user)
    assert b'confirm2fa = true' in admin_client.get(url, follow=True).content


def test_edit_user_page_hides_reset_on_your_own_account(client, admin_user):
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    assert b'confirm2fa = true' not in client.get(f'/add_user/{admin_user.id}', follow=True).content


# ---------- session verification (defence in depth) ----------

def test_session_with_device_but_no_code_is_signed_out(client, regular_user):
    enrol(regular_user)
    client.force_login(regular_user)  # a login path that skipped the code step
    response = client.get(reverse('main'))
    assert response.status_code == 302
    assert response['Location'] == '/common/login/'
    assert not is_logged_in(client)


# ---------- Django admin ----------

def test_admin_login_form_is_never_used(client):
    response = client.get(reverse('admin:login') + '?next=/admin/')
    assert response.status_code == 302
    assert response['Location'].startswith('/common/login/?next=')


def test_admin_requires_verified_session_when_device_exists(client, admin_user):
    enrol(admin_user)
    login_with_2fa(client, admin_user, 'admin-pass')
    assert client.get(reverse('admin:index')).status_code == 200


def test_admin_as_normal_user_is_forbidden_not_looped(user_client):
    assert user_client.get(reverse('admin:login')).status_code == 403


# ---------- impersonation ----------

def test_impersonation_keeps_admin_verified_and_blocks_2fa_management(client, admin_user, regular_user):
    enrol(admin_user)
    enrol(regular_user)  # the target has 2FA too: acting as them must not ask for a code
    login_with_2fa(client, admin_user, 'admin-pass')

    start = client.get('/impersonate/%d/start' % regular_user.id)
    assert start.status_code == 302
    assert client.get(reverse('main')).status_code == 200
    # Acting as bob: cannot touch bob's second factor.
    assert client.get(reverse('common:twofactor')).status_code == 302
    assert client.post(reverse('common:twofactor_disable'), {'password': 'bob-pass'}).status_code == 302
    assert twofactor.has_2fa(regular_user)

    client.get('/impersonate/stop')
    # Back as the admin, and still verified (no sign-out, admin site open).
    assert client.get(reverse('admin:index')).status_code == 200


# ---------- reset command ----------

def test_reset_2fa_command(admin_user):
    enrol(admin_user)
    call_command('reset_2fa', 'admin')
    assert not twofactor.has_2fa(admin_user)
    assert Activity_log.objects.filter(action='2FA_RESET', user_affected='admin').exists()


def test_reset_2fa_unknown_user():
    from django.core.management.base import CommandError
    with pytest.raises(CommandError):
        call_command('reset_2fa', 'ghost')


# ---------- i18n ----------

@pytest.mark.parametrize('lang', ['de', 'es', 'fr', 'ja', 'pt-br', 'ru', 'zh-hans'])
def test_two_factor_strings_are_translated(lang):
    from django.utils import translation
    from django.utils.translation import gettext, ngettext
    with translation.override(lang):
        for msgid in ('Backup codes', 'Invalid code.', 'Verify', 'Set up two-factor authentication'):
            assert gettext(msgid) != msgid, (lang, msgid)
        assert ngettext('%(n)s backup code left.', '%(n)s backup codes left.', 3) != '%(n)s backup codes left.'


def test_setup_page_renders_translated(client, regular_user, settings):
    client.force_login(regular_user)
    response = client.get('/es/common/2fa/setup/')
    assert response.status_code == 200
    assert 'Configurar la autenticación en dos pasos' in response.content.decode()
