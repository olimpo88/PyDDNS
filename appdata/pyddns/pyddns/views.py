#encoding:utf-8
from django.contrib.auth import authenticate, login as djlogin, logout as djlogout
from django.contrib.auth.decorators import login_required
#from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect
#from django.utils import simplejson
from django.shortcuts import render_to_response, render
from django.template  import RequestContext
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Max, Count
from django.contrib.auth.models import User

import json
import base64
import requests

#from common.utils import getForwardedFor
#from servers.models import Activity_log
from common.models import Activity_log
from datetime import datetime, timedelta
from django.conf import settings
from pyddns.models import SubDomain


@user_passes_test(lambda u: u.is_superuser)

@login_required
def main(request):

	admin=False
	if request.user.is_superuser:
		admin=True
	name = request.user.first_name
	username = request.user.username
	actividad=Activity_log.objects.filter(user_affected=username,action="SYNC")

	my_subdomains=SubDomain.objects.filter(user=request.user)

	last_activity = Activity_log.objects.filter(action="SYNC",code="good")
	last_activity = last_activity.values('domain','ip').annotate(date=Max('date')).order_by('domain')

	domain=settings.DNS_DOMAIN
	info_domains=[]
	for sub in my_subdomains:
		ip = ""
		date = ""
		for activity in last_activity:
			print sub.name
			print activity['domain']
			if sub.name == activity['domain'].split(".")[0]:
				ip = activity['ip']
				print activity
				date = activity['date']
		obj ={
			'domain': "%s.%s"%(sub.name, domain),
			'ip': ip,
			'date': date
		}
		print obj
		info_domains.append(obj)

	
	ip_x_forwarded=None
 	if 'HTTP_X_FORWARDED_FOR' in request.META:
 		ip_x_forwarded=request.META['HTTP_X_FORWARDED_FOR']
	paginator = Paginator(actividad, 10) # Show 25 contacts per page
	page = request.GET.get('page')
	try:
		list_activity = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		list_activity = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		list_activity = paginator.page(paginator.num_pages)
		
	return render_to_response("dash.html",{'name':name, 'username':username, 'list_activity':list_activity, 'last_activity':last_activity, 'my_subdomains':my_subdomains, 'info_domains':info_domains ,'ip_x_forwarded':ip_x_forwarded, 'admin':admin })

@login_required
def manage(request):
	domains=my_subdomains=SubDomain.objects.filter(user=request.user).order_by('name')

	paginator = Paginator(domains, 10) # Show 25 contacts per page
	page = request.GET.get('page')
	try:
		list_domains = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		list_domains = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		list_domains = paginator.page(paginator.num_pages)

	return render_to_response("manage.html",{ 'list_domains': list_domains})

@login_required
def users(request):
	users=User.objects.all()

	paginator = Paginator(users, 10) # Show 25 contacts per page
	page = request.GET.get('page')
	try:
		list_users = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		list_users = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		list_users = paginator.page(paginator.num_pages)

	return render_to_response("users.html",{ 'list_users': list_users})





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

	Activity_log(action='SYNC', agent=agent , ip=ip, code=return_code, xforward=ip_x_forwarded, user_affected=username, domain=domain, result="%s"%(message)).save()

	return HttpResponse(json.dumps(myjson))






def set_ip(request,domain,ip):


	message=""
	subdomain=domain.split(".")[0]
	print 'http://%s:%s/update?secret=%s&domain=%s&addr=%s'%(settings.DNS_HOST,settings.DNS_API_PORT,settings.DNS_SHARED_SECRET,subdomain,ip)
	r = requests.get('http://%s:%s/update?secret=%s&domain=%s&addr=%s'%(settings.DNS_HOST,settings.DNS_API_PORT,settings.DNS_SHARED_SECRET,subdomain,ip))
	#print r.json()
	#print r.json()['Success']
	if r.json()['Success']:
		return_code = "good"
		message = "The updatewas successful and the hostname is now updated"
	else:
		return_code = "unknown"
		message = "The APP not sinc bind"
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

	cant_fails=Activity_log.objects.filter(action='SYNC', ip=ip, date__gt=(datetime.now()-timedelta(minutes=10)), result__startswith='False').count()
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
								message="The hostname specified does not exist in this user account"
						else:
							return_code="badauth"
							message="The username and password pair do not match a real user"
					else:
						return_code="unknown"
						message="Incorrect authentication format"
				else:
					return_code="unknown"
					message="Incorrect authentication format"
			else:
				return_code="unknown"
				message="Missing header HTTP_AUTHORIZATION"
		else:
			return_code="badagent"
			message="Missing header HTTP_USER_AGENT"
	else:
		return_code="abuse"
		message="You have exceeded the maximum number of attempts"	


	print return_code
	Activity_log(action='SYNC', agente=agent , ip=ip, code=return_code, xforward=ip_x_forwarded, user_affected=username, domain=domain, result="%s"%(message)).save()
	return HttpResponse(return_code)
