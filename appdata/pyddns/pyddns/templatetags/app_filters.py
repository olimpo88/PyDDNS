from django import template
from datetime import date, timedelta
from django.contrib.auth.models import User
from pyddns.models import SubDomain

register = template.Library()

@register.filter(name='count_domain')
def count_domain(user):
	count = SubDomain.objects.filter(user=user).count()
	return count