#encoding:utf-8
from django.contrib.auth import authenticate, login as djlogin, logout as djlogout
from django.contrib.auth.decorators import login_required
#from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseRedirect
#from django.utils import simplejson
from django.shortcuts import render
from django.template  import RequestContext
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Max, Count
from django.contrib.auth.models import User

import json
import base64
import requests

from common.models import Activity_log
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from pyddns.models import SubDomain
from django.db.models import Q
from common import twofactor
from common.utils import get_client_ip
from django_otp import devices_for_user, login as otp_login
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _

import ipaddress
import re
import socket
import dns.resolver
import logging
logger = logging.getLogger('django')

@login_required
def main(request,id_user=None):
    logger.info("LOGIN")
    admin=False
    see_user=False

    own_admin=False
    if settings.OWN_ADMIN=="1" and not id_user:
        own_admin=True

    if request.user.is_superuser:
        admin=True

    if id_user:
        user=User.objects.get(id=id_user)
        see_user=True
    else:
        user=request.user
        id_user=request.user.id

    name = user.first_name
    username = user.username
    actividad = Activity_log.objects.filter(user_affected=username, action="SYNC")

    my_subdomains = SubDomain.objects.filter(user=user).order_by('name')
    domain = settings.DNS_DOMAIN

    ip_x_forwarded = None
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        ip_x_forwarded = request.META['HTTP_X_FORWARDED_FOR']

    # Stats over the last 24 hours for the cards on the dashboard.
    last_24h = timezone.now() - timedelta(hours=24)
    syncs_24h = actividad.filter(date__gte=last_24h).count()
    failed_24h = actividad.filter(date__gte=last_24h).exclude(code__in=['good', 'nochg']).count()

    paginator = Paginator(actividad, 10)
    page = request.GET.get('page')
    try:
        list_activity = paginator.page(page)
    except PageNotAnInteger:
        list_activity = paginator.page(1)
    except EmptyPage:
        list_activity = paginator.page(paginator.num_pages)

    return render(request, "dash.html", {
        'name': name,
        'username': username,
        'list_activity': list_activity,
        'my_subdomains': my_subdomains,
        'ip_x_forwarded': ip_x_forwarded,
        'admin': admin,
        'see_user': see_user,
        'domain': domain,
        'id_user': id_user,
        'own_admin': own_admin,
        'view_user': user,
        'syncs_24h': syncs_24h,
        'failed_24h': failed_24h,
    })

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

    return render(request,"manage.html",{ 'list_domains': list_domains})


@user_passes_test(lambda u: u.is_superuser,login_url='/common/permission_denied')
def users(request, buscar=None):
    #print buscar
    users=User.objects.all().order_by('username')

    if buscar:
        users=users.filter( Q(first_name__icontains=buscar) | Q(last_name__icontains=buscar) | Q(username__icontains=buscar) )
    else:
        buscar=""
    paginator = Paginator(users, 10)
    page = request.GET.get('page')
    try:
        list_users = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        list_users = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        list_users = paginator.page(paginator.num_pages)
    return render(request,"users.html",{ 'list_users': list_users, "buscar":buscar})


@user_passes_test(lambda u: u.is_superuser,login_url='/common/permission_denied')
def domains(request, buscar=None):
    subdomains=SubDomain.objects.all().order_by('name')

    #print buscar
    if buscar:
        subdomains=subdomains.filter( name__icontains=buscar )
    else:
        buscar=""

    domain=settings.DNS_DOMAIN

    paginator = Paginator(subdomains, 10)
    page = request.GET.get('page')
    try:
        list_subdomains = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        list_subdomains = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        list_subdomains = paginator.page(paginator.num_pages)
    return render(request,"subdomains.html",{ 'list_subdomains': list_subdomains, "buscar":buscar, 'domain':domain })


@user_passes_test(lambda u: u.is_superuser,login_url='/common/permission_denied')
def add_user(request,id_user=None):
    user=None
    if id_user:
        try:
            user=User.objects.get(id=id_user)
        except User.DoesNotExist:
            pass
    # Resetting your own 2FA is not offered here (see reset_user_2fa).
    can_reset_2fa = bool(user and user.id != request.user.id and twofactor.has_2fa(user))
    return render(request,"add_user.html",{'user':user, 'can_reset_2fa': can_reset_2fa})

SUBDOMAIN_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,62}$')


@login_required
def add_subdomain(request):
    myjson = {
        'error': "",
        'success': False,
    }

    if "subdomain" in request.POST.keys():
        subdomain = request.POST['subdomain']
        id_user = request.POST['id_user']

        if not SUBDOMAIN_RE.match(subdomain):
            myjson['error'] = "invalid subdomain"
            return HttpResponse(json.dumps(myjson))

        try:
            user = User.objects.get(id=id_user)
        except (User.DoesNotExist, ValueError):
            myjson['error'] = "invalid user"
            return HttpResponse(json.dumps(myjson))

        try:
            subdomain = SubDomain.objects.get(name=subdomain)
            myjson['error'] = "exist"
        except SubDomain.DoesNotExist:
            admin = request.user.is_superuser
            user_login = request.user

            if admin or user_login == user:
                SubDomain(user=user, name=subdomain).save()
                myjson['success'] = True
            else:
                myjson['error'] = "Not permission"
    return HttpResponse(json.dumps(myjson))


@user_passes_test(lambda u: u.is_superuser,login_url='/common/permission_denied')
def set_user(request):
    myjson = {
        'error': "",
        'success': False,
    }
    #print request.POST
    if "username" in request.POST.keys():
        username=request.POST['username']
        name=request.POST['name']
        last_name=request.POST['last_name']
        email=request.POST['email']
        password=request.POST['password']
        is_admin=request.POST['is_admin']

        if is_admin=="1":
            is_admin=True
        else:
            is_admin=False


        try:
            user_exist= User.objects.get(username=username)
            myjson['error']= "username exist"
            return HttpResponse(json.dumps(myjson))
        except User.DoesNotExist:
            user = User.objects.create_user(username=username,
                                             email=email,
                                             password=password)
            if password:
                #user.password=password
                user.set_password(password)
            user.first_name=name
            user.last_name=last_name
            user.is_superuser=is_admin
            user.save()
            myjson['success']= True
        Activity_log(action='EDIT USER', xforward=get_client_ip(request), user_affected=request.user, result="Edit User --> name: %s"%user).save()


    elif "id_user" in request.POST.keys():
        name=request.POST['name']
        last_name=request.POST['last_name']
        email=request.POST['email']
        password=request.POST['password']
        is_admin=request.POST['is_admin']
        user= User.objects.get(id=request.POST['id_user'])
        if is_admin=="1":
            is_admin=True
        else:
            is_admin=False
        user.first_name=name
        user.last_name=last_name
        user.is_superuser=is_admin
        user.email=email
        if password:
            #user.password=password
            #print password
            user.set_password(password)
        user.save()
        myjson['success']= True
        Activity_log(action='SET USER', xforward=get_client_ip(request), user_affected=request.user, result="Add User --> name: %s"%user).save()
    else:
        myjson['error']= "No se pasaron los datos por post"

    return HttpResponse(json.dumps(myjson))



@user_passes_test(lambda u: u.is_superuser,login_url='/common/permission_denied')
def delet_user(request):
    myjson = {
        'error': "",
        'success': False,
    }
    if "id_user" in request.POST.keys():
        id_user=request.POST['id_user']
        user= User.objects.get(id=request.POST['id_user'])
        user.delete()
        myjson['success']= True
        Activity_log(action='DELET USER', xforward=get_client_ip(request), user_affected=request.user, result="Delet User --> name: %s"%user).save()
    else:
        myjson['error']= "No se pasaron los datos por post"
    return HttpResponse(json.dumps(myjson))

@user_passes_test(lambda u: u.is_superuser, login_url='/common/permission_denied')
@require_POST
def reset_user_2fa(request):
    """Admin-only: blank another user's two-factor setup (lost phone).

    The user keeps their password; they sign in with it alone and can enrol
    again (admins under ADMIN_FORCE_2FA are sent to enrol at that sign-in).
    Resetting your own is refused: that would let a hijacked admin session
    strip the admin's own second factor.
    """
    myjson = {'error': '', 'success': False}
    try:
        target = User.objects.get(id=request.POST.get('id_user', ''))
    except (User.DoesNotExist, ValueError):
        myjson['error'] = _('Failed')
        return HttpResponse(json.dumps(myjson), status=404)
    if target.id == request.user.id:
        myjson['error'] = _('Failed')
        return HttpResponse(json.dumps(myjson), status=403)
    removed = twofactor.remove_2fa(target)
    Activity_log(
        action='2FA_RESET',
        xforward=get_client_ip(request),
        user_affected=target.get_username(),
        result='Reset by admin %s (%d device(s) removed)' % (request.user.get_username(), removed),
    ).save()
    myjson['success'] = True
    return HttpResponse(json.dumps(myjson))


@user_passes_test(lambda u: u.is_superuser, login_url='/common/permission_denied')
def impersonate(request, user_id):
    """Admin-only: switch the active session to another user.

    The original admin user id is stored in the session so the banner can
    offer a 'Stop impersonating' action. djlogin() flushes the session when
    the user changes, so we record the impersonator AFTER login.
    """
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseRedirect('/users/')
    if target.id == request.user.id or not target.is_active:
        return HttpResponseRedirect('/users/')

    admin_id = request.user.id
    admin_username = request.user.username
    # Remember whether the admin had passed the second factor: djlogin()
    # flushes the session, and stop_impersonating() must restore it.
    admin_verified = request.user.is_verified()
    djlogin(request, target, backend='django.contrib.auth.backends.ModelBackend')
    request.session['_impersonator_id'] = admin_id
    request.session['_impersonator_verified'] = admin_verified
    request.session.save()
    Activity_log(
        action='IMPERSONATE_START',
        xforward=get_client_ip(request),
        user_affected=target.username,
        result='Admin %s -> %s' % (admin_username, target.username),
    ).save()
    return HttpResponseRedirect('/main/')


@login_required
def stop_impersonating(request):
    impersonator_id = request.session.pop('_impersonator_id', None)
    was_verified = request.session.pop('_impersonator_verified', False)
    if not impersonator_id:
        return HttpResponseRedirect('/main/')
    try:
        impersonator = User.objects.get(id=impersonator_id)
    except User.DoesNotExist:
        return HttpResponseRedirect('/main/')
    target_username = request.user.username
    djlogin(request, impersonator, backend='django.contrib.auth.backends.ModelBackend')
    if was_verified:
        device = next(iter(devices_for_user(impersonator)), None)
        if device is not None:
            otp_login(request, device)
    Activity_log(
        action='IMPERSONATE_STOP',
        xforward=get_client_ip(request),
        user_affected=impersonator.username,
        result='Restored %s (was acting as %s)' % (impersonator.username, target_username),
    ).save()
    return HttpResponseRedirect('/users/')


@login_required
def delet_domain(request):
    myjson = {
        'error': "",
        'success': False,
    }

    if "id_domain" in request.POST.keys():
        id_domain=request.POST['id_domain']
        domain= SubDomain.objects.get(id=id_domain)
        domain_name=domain.name
        domain_user=domain.user

        if request.user.is_superuser or request.user==domain_user:
            domain.delete()
            myjson['success']= True
            Activity_log(action='DELET DOMAIN', xforward=get_client_ip(request), user_affected=domain_user, result="Delet domain --> name: %s"%domain_name).save()
        else:
            myjson['error']= "permission"
    else:
        myjson['error']= "No se pasaron los datos por post"
    return HttpResponse(json.dumps(myjson))



@login_required
def set_ip_web(request, domain, ip):
    myjson = {
        'message': '',
        'success': False,
    }

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        myjson['message'] = 'invalid ip'
        return HttpResponse(json.dumps(myjson))

    subdomain = domain.split(".")[0]
    if not SUBDOMAIN_RE.match(subdomain):
        myjson['message'] = 'invalid subdomain'
        return HttpResponse(json.dumps(myjson))

    user = request.user
    admin = user.is_superuser

    try:
        subdomain_obj = SubDomain.objects.get(name=subdomain)
    except SubDomain.DoesNotExist:
        myjson['message'] = 'unknown subdomain'
        return HttpResponse(json.dumps(myjson))

    try:
        check_valid_subdomain = SubDomain.objects.get(user=user, name=subdomain)
    except SubDomain.DoesNotExist:
        check_valid_subdomain = False

    if check_valid_subdomain or admin:

        agent=""
        ip_x_forwarded=""
        username = user.username
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            ip_x_forwarded=request.META['HTTP_X_FORWARDED_FOR']

        if 'HTTP_USER_AGENT' in request.META:
            agent=request.META['HTTP_USER_AGENT']

        return_code, message = set_ip(request,domain,ip)
        if return_code== "good":
            myjson['success'] = True
        else:
            myjson['message'] = message

        #print return_code
        #if return_code != "nochg":

        register=False
        last_activity=Activity_log.objects.filter(user_affected=username).last()
        if last_activity:
            if last_activity.code != return_code or return_code == "good":
                register=True
        else:
            register=True

        if register:
            Activity_log(action='SYNC', agent=agent , ip=ip, code=return_code, xforward=ip_x_forwarded, user_affected=subdomain_obj.user.username, domain=domain, result="%s"%(message)).save()

    return HttpResponse(json.dumps(myjson))






def set_ip(request, domain, ip):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [socket.gethostbyname(settings.DNS_HOST)]
    try:
        ip_dig = resolver.resolve(domain, "A")[0]
    except Exception:
        ip_dig = None

    if str(ip_dig) != str(ip):
        subdomain = domain.split(".")[0]
        r = requests.get(
            'http://%s:%s/update' % (settings.DNS_HOST, settings.DNS_API_PORT),
            params={
                'secret': settings.DNS_SHARED_SECRET,
                'domain': subdomain,
                'addr': ip,
            },
            timeout=10,
        )
        if r.json()['Success']:
            return "good", "The update was successful and the hostname is now updated"
        return "dnserr", "The APP not sinc bind"
    return "nochg", "It already exists"



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

    verified_agent=False
    if settings.DNS_ALLOW_AGENT:
        list_agent_allow=settings.DNS_ALLOW_AGENT.split(",")
        if list_agent_allow:
            for a in list_agent_allow:
                if a in request.META['HTTP_USER_AGENT']:
                    verified_agent=True
    else:
        verified_agent=True

    cant_fails=Activity_log.objects.filter(action='SYNC', ip=ip, date__gt=(timezone.now()-timedelta(minutes=10)), result__startswith='False').count()
    if cant_fails<10:
        if verified_agent:
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2:
                    if auth[0].lower() == "basic":
                        try:
                            username, passwd = base64.b64decode(auth[1]).decode("utf-8", "ignore").split(':', 1)
                        except (ValueError, base64.binascii.Error):
                            username, passwd = "", ""

                        user_fails = Activity_log.objects.filter(
                            action='SYNC',
                            user_affected=username,
                            date__gt=(timezone.now() - timedelta(minutes=10)),
                            result__startswith='False',
                        ).count() if username else 0

                        if user_fails >= 5:
                            return_code = "abuse"
                            message = "Too many failed attempts for this user"
                        else:
                            if settings.DEBUG:
                                logger.debug("dyndns2 auth attempt user=%r", username)
                            user = authenticate(username=username, password=passwd)
                            if user is not None and user.is_active:

                                user_subdomains = SubDomain.objects.filter(user=user)
                                valid_domain = False

                                for sub in user_subdomains:
                                    if domain == "%s.%s" % (sub.name, settings.DNS_DOMAIN):
                                        valid_domain = True

                                if valid_domain:
                                    return_code, message = set_ip(request, domain, ip)
                                else:
                                    return_code = "nohost"
                                    message = "The hostname specified does not exist in this user account"
                            else:
                                return_code = "badauth"
                                message = "The username and password pair do not match a real user"
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

    #if return_code != "nochg":
    register=False
    last_activity=Activity_log.objects.filter(user_affected=username).last()
    if last_activity:
        if last_activity.code != return_code or return_code == "good":
            register=True
    else:
        register=True

    if register:
        Activity_log(action='SYNC', agent=agent , ip=ip, code=return_code, xforward=ip_x_forwarded, user_affected=username, domain=domain, result="%s"%(message)).save()

    return HttpResponse(return_code)
