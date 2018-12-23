from django import template
from datetime import date, timedelta
from django.contrib.auth.models import User
from pyddns.models import SubDomain
from common.models import Activity_log
from django.conf import settings


register = template.Library()

@register.filter(name='count_domain')
def count_domain(user):
	count = SubDomain.objects.filter(user=user).count()
	return count

@register.filter(name='last_ip')
def last_ip(subdomain):
	domain='%s.%s'%(subdomain,settings.DNS_DOMAIN)
	try:
		last_activity=Activity_log.objects.filter(action="SYNC", code="good",domain=domain).latest('date')
		return last_activity.ip
	except Activity_log.DoesNotExist:
		return "---"

@register.filter(name='last_update')
def last_update(subdomain):
	domain='%s.%s'%(subdomain,settings.DNS_DOMAIN)
	try:
		last_activity=Activity_log.objects.filter(action="SYNC", code="good",domain=domain).latest('date')
		return last_activity.date
	except Activity_log.DoesNotExist:
		return "---"	
