#encoding:utf-8
from django.contrib.auth import authenticate, login as djlogin, logout as djlogout
from django.contrib.auth.decorators import login_required
#from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect
#from django.utils import simplejson
from django.shortcuts import render
from django.template  import RequestContext
import json

#from servers.models import Activity_log
from common.utils import get_client_ip
from common.models import Activity_log
from datetime import timedelta
from django.utils import timezone
from pyddns.views import main
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login, match_token
from common import twofactor
import base64
import requests


def _safe_next(request, value):
	"""Only same-site relative targets are honoured after login."""
	if value and url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
		return value
	return ''


def dologin(request):
	myjson = {
		'errors': {},
		'message': '',
		'success': False,
		'redirect': '',
		'sync': ''
	}
	username=request.POST['username']
	if request.session.test_cookie_worked():
		cant_fails=Activity_log.objects.filter(action='DOLOGIN', xforward=get_client_ip(request), date__gt=(timezone.now()-timedelta(minutes=10)), result__startswith='False').count()
		if cant_fails>=5:
			myjson['errors']['reason']=u'Ha superado la cantidad máxima de intentos.'
		else:
			user = authenticate(username=username,
					password=request.POST['password'])
			if user is not None:
				if user.is_active and twofactor.user_has_confirmed_device(user):
					# Password is right but the account has a second factor:
					# do NOT log in yet, wait for the code (verify2fa).
					request.session.delete_test_cookie()
					request.session[twofactor.PENDING_KEY] = {
						'uid': user.pk,
						'ts': timezone.now().timestamp(),
						'fails': 0,
						'next': _safe_next(request, request.POST.get('next', '')),
					}
					myjson['two_factor'] = True
					myjson['errors']['reason'] = '2FA requerido.'
				elif user.is_active:
					request.session.delete_test_cookie()
					djlogin(request, user)
					myjson['success'] = True
					myjson['message'] = 'Bienvenido, %s!' % (user.get_full_name(),)
					myjson['redirect'] = _safe_next(request, request.POST.get('next', '')) or '/main/'
					myjson['errors']['reason'] = 'Login correcto.'
				else:
					myjson['errors']['reason'] = 'Cuenta deshabilitada.'
			else:
				myjson['errors']['reason'] = 'Usuario y/o clave invalida.'
	else:
		myjson['errors']['reason'] = 'Por favor, habilite las Cookies en su navegador.'
	# A password-OK / code-pending login is not a failure: it must not count
	# towards the per-IP lockout (which matches results starting with 'False').
	outcome = 'Pending' if myjson.get('two_factor') else myjson['success']
	Activity_log(action='DOLOGIN', xforward=get_client_ip(request), user_affected=username, result="%s - %s"%(outcome, myjson['errors']['reason'])).save()

	return HttpResponse(json.dumps(myjson))


def verify2fa(request):
	"""Second login step: validate the TOTP / backup code for the user whose
	password was accepted by dologin, then complete the login."""
	myjson = {'errors': {}, 'success': False, 'redirect': '', 'restart': False}
	if request.method != 'POST':
		return HttpResponse(status=405)
	pending = request.session.get(twofactor.PENDING_KEY)
	ip = get_client_ip(request)
	user = None
	if not twofactor.pending_session_valid(pending):
		request.session.pop(twofactor.PENDING_KEY, None)
		myjson['restart'] = True
		myjson['errors']['reason'] = _('The verification expired. Please sign in again.')
	else:
		user = get_user_model().objects.filter(pk=pending['uid'], is_active=True).first()
		recent_fails = Activity_log.objects.filter(action='LOGIN_2FA', xforward=ip, date__gt=(timezone.now()-timedelta(minutes=10)), result__startswith='False').count()
		if user is None:
			request.session.pop(twofactor.PENDING_KEY, None)
			myjson['restart'] = True
			myjson['errors']['reason'] = _('Account disabled.')
		elif recent_fails >= 10:
			myjson['errors']['reason'] = _('Too many attempts. Try again later.')
		else:
			token = twofactor.normalize_token(request.POST.get('token', ''))
			device = match_token(user, token) if token else None
			if device is not None:
				request.session.pop(twofactor.PENDING_KEY, None)
				djlogin(request, user, backend='django.contrib.auth.backends.ModelBackend')
				otp_login(request, device)
				myjson['success'] = True
				myjson['redirect'] = pending.get('next') or '/main/'
				myjson['errors']['reason'] = 'Login correcto.'
			else:
				pending['fails'] = pending.get('fails', 0) + 1
				if pending['fails'] >= twofactor.PENDING_MAX_ATTEMPTS:
					# Too many wrong codes: make them start over from the password.
					request.session.pop(twofactor.PENDING_KEY, None)
					myjson['restart'] = True
				else:
					request.session[twofactor.PENDING_KEY] = pending
				myjson['errors']['reason'] = _('Invalid code.')
	if user is not None:
		Activity_log(action='LOGIN_2FA', xforward=ip, user_affected=user.get_username(), result="%s - %s"%(myjson['success'], myjson['errors']['reason'])).save()
	return HttpResponse(json.dumps(myjson))


def login(request):
	request.session.set_test_cookie()
	return render(request,"login.html", {'next': _safe_next(request, request.GET.get('next', ''))})

def permission_denied(request):
	return render(request,"permission_denied.html")

@login_required
def logout(request, next_page = '/common/login/'):
	djlogout(request)
	return HttpResponseRedirect(next_page)

def sin_permiso(request):
	return render(request,"sin_permiso.html")