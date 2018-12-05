#encoding:utf-8
from django.contrib.auth import authenticate, login as djlogin, logout as djlogout
from django.contrib.auth.decorators import login_required
#from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect
#from django.utils import simplejson
from django.shortcuts import render_to_response, render
from django.template  import RequestContext
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Max, Count
import json
import base64
import requests

#from common.utils import getForwardedFor
#from servers.models import Activity_log
from common.models import Activity_log
from datetime import datetime, timedelta
from django.conf import settings
from pyddns.models import SubDomain

@login_required
def main(request):
	name = request.user.first_name
	username = request.user.username
	actividad=Activity_log.objects.filter(afectado=username,action="SYNC")

	my_subdomains=SubDomain.objects.filter(user=request.user)

	last_activity = Activity_log.objects.filter(action="SYNC",codigo="good")
	last_activity = last_activity.values('dominio','origen').annotate(fecha=Max('fecha_hora')).order_by('dominio')

	dominio=settings.DNS_DOMAIN
	info_dominios=[]
	for sub in my_subdomains:
		ip = ""
		fecha = ""
		for activity in last_activity:
			print sub.name
			print activity['dominio']
			if sub.name == activity['dominio'].split(".")[0]:
				ip = activity['origen']
				fecha = activity['fecha']
		obj ={
			'dominio': "%s.%s"%(sub.name, dominio),
			'ip': ip,
			'fecha': fecha
		}

		info_dominios.append(obj)

	
	ip_x_forwarded=None
 	if 'HTTP_X_FORWARDED_FOR' in request.META:
 		ip_x_forwarded=request.META['HTTP_X_FORWARDED_FOR']
	paginator = Paginator(actividad, 10) # Show 25 contacts per page
	page = request.GET.get('page')
	try:
		lista_actividad = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		lista_actividad = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		lista_actividad = paginator.page(paginator.num_pages)
		
	return render_to_response("dash.html",{'name':name, 'username':username, 'lista_actividad':lista_actividad, 'last_activity':last_activity, 'my_subdomains':my_subdomains, 'dominio':dominio, 'info_dominios':info_dominios ,'ip_x_forwarded':ip_x_forwarded })







def set_ip_web(request,domain,ip,):
	myjson = {
		'message': '',
		'success': False,
	}

	agent=""
	ip_x_forwarded=""
	username = request.user.username
 	if 'HTTP_X_FORWARDED_FOR' in request.META:
 		ip_x_forwarded=request.META['HTTP_X_FORWARDED_FOR']


	if 'HTTP_USER_AGENT' in request.META:
		agent=request.META['HTTP_USER_AGENT']

	return_code, message = set_ip(request,domain,ip)
	print "llego"
	print return_code
	print message
	if return_code== "good":
		myjson['success'] = True
	else:
		myjson['message'] = message

	Activity_log(action='SYNC', agente=agent , origen=ip, codigo=return_code, ip_origen=ip_x_forwarded, afectado=username, dominio=domain, resultado="%s"%(message)).save()

	return HttpResponse(json.dumps(myjson))






def set_ip(request,domain,ip):


	message=""
	subdomain=domain.split(".")[0]
	#print 'http://%s:%s/update?secret=%s&domain=%s&addr=%s'%(settings.DNS_HOST,settings.DNS_API_PORT,settings.DNS_SHARED_SECRET,username,ip)
	r = requests.get('http://%s:%s/update?secret=%s&domain=%s&addr=%s'%(settings.DNS_HOST,settings.DNS_API_PORT,settings.DNS_SHARED_SECRET,subdomain,ip))
	#print r.json()
	#print r.json()['Success']
	if r.json()['Success']:
		return_code = "good"
		message = "Actualización de IP exitosa"
	else:
		return_code = "unknown"
		message = "La APP no pudo sincronizar con bind"
	#print return_code
	return return_code, message




def updateip(request):

 	return_code="unknown"
 	username=""
 	domain=""
 	ip=""
 	ip_x_forwarded=""
 	hostname=""
 	message=""
 	agent=""

 	if request.method == 'GET':
 		if 'hostname' in request.GET: 
 			domain=request.GET['hostname']
 		if 'myip' in request.GET:
 			ip=request.GET['myip']

 	if 'HTTP_X_FORWARDED_FOR' in request.META:
 		ip_x_forwarded=request.META['HTTP_X_FORWARDED_FOR']

 	if 'HTTP_USER_AGENT' in request.META:
 		agent=request.META['HTTP_USER_AGENT']

 	list_agent_allow=settings.DNS_ALLOW_AGENT.split(",")
 	verified_agent=False
 	if list_agent_allow:
 		for a in list_agent_allow:
 			if a in request.META['HTTP_USER_AGENT']:
 				verified_agent=True
 	else:
 		verified_agent=True

	cant_fails=Activity_log.objects.filter(action='SYNC', origen=ip, fecha_hora__gt=(datetime.now()-timedelta(minutes=10)), resultado__startswith='False').count()
	if cant_fails<10:
	 	if verified_agent:
			if 'HTTP_AUTHORIZATION' in request.META:
				auth = request.META['HTTP_AUTHORIZATION'].split()
				if len(auth) == 2:
					if auth[0].lower() == "basic":
						username, passwd = base64.b64decode(auth[1]).split(':')
						user = authenticate(username=username, password=passwd)
						if user is not None and user.is_active:

							user_subdomains=SubDomain.objects.filter(user=user)
							valid_domain=False

							for sub in user_subdomains:
								if domain == "%s.%s"%(sub.name,settings.DNS_DOMAIN):
									valid_domain=True
							
							if valid_domain:
								return_code, message = set_ip(request,domain,ip)
							else:
								return_code="nohost"
								message="El dominio no es valido"
						else:
							return_code="badauth"
							message="El usuario o contraseña incorrecto o esta deshabilitado"
					else:
						return_code="unknown"
						message="Formato de autenticacion incorrecto"
				else:
					return_code="unknown"
					message="Formato de autenticacion incorrecto"
			else:
				return_code="unknown"
				message="Falta de cabecera HTTP_AUTHORIZATION"
		else:
			return_code="badagent"
			message="Falta de cabecera HTTP_USER_AGENT"
	else:
		return_code="abuse"
		message="Ha superado la cantidad máxima de intentos."	


	print return_code
	Activity_log(action='SYNC', agente=agent , origen=ip, codigo=return_code, ip_origen=ip_x_forwarded, afectado=username, dominio=domain, resultado="%s"%(message)).save()
	return HttpResponse(return_code)
