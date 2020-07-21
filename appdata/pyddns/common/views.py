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
from common.utils import getForwardedFor
from common.models import Activity_log
from datetime import datetime, timedelta
from pyddns.views import main
import base64
import requests

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
		cant_fails=Activity_log.objects.filter(action='DOLOGIN', xforward=getForwardedFor(request), date__gt=(datetime.now()-timedelta(minutes=10)), result__startswith='False').count()
		if cant_fails>=5:
			myjson['errors']['reason']=u'Ha superado la cantidad máxima de intentos.'
		else:
			user = authenticate(username=username,
					password=request.POST['password'])
			if user is not None:
				if user.is_active:
					request.session.delete_test_cookie()
					djlogin(request, user)
					myjson['success'] = True
					myjson['message'] = 'Bienvenido, %s!' % (user.get_full_name(),)
					myjson['redirect'] = '/common/main/'
					myjson['errors']['reason'] = 'Login correcto.'
				else:
					myjson['errors']['reason'] = 'Cuenta deshabilitada.'
			else:
				myjson['errors']['reason'] = 'Usuario y/o clave invalida.'
	else:
		myjson['errors']['reason'] = 'Por favor, habilite las Cookies en su navegador.'
	Activity_log(action='DOLOGIN', xforward=getForwardedFor(request), user_affected=username, result="%s - %s"%(myjson['success'], myjson['errors']['reason'])).save()

	return HttpResponse(json.dumps(myjson))


def login(request):
	request.session.set_test_cookie()
	return render(request,"login.html")

def permission_denied(request):
	return render(request,"permission_denied.html")

@login_required
def logout(request, next_page = '/common/login/'):
	djlogout(request)
	return HttpResponseRedirect(next_page)

def sin_permiso(request):
	return render(request,"sin_permiso.html")