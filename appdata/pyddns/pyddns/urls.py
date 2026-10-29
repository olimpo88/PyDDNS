"""pyddns URL Configuration"""
import os

from django.contrib import admin
from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.i18n import i18n_patterns

from common.views import *
from pyddns.views import *


urlpatterns = [
    re_path(r'^nic/update', updateip),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
]

if getattr(settings, 'ENABLE_REST_API', False):
    urlpatterns.append(re_path(r'^api/', include('api.urls')))

urlpatterns += i18n_patterns(
    re_path(r'^main/(?P<id_user>.+)', main),
    re_path(r'^main/', main, name="main"),
    re_path(r'^users/(?P<buscar>.+)', users),
    re_path(r'^users/', users, name='users'),
    re_path(r'^domains/(?P<buscar>.+)', domains),
    re_path(r'^domains/', domains, name="domains"),
    re_path(r'^add_user/(?P<id_user>\d+)', add_user),
    re_path(r'^add_user/', add_user, name="add_user"),
    re_path(r'^add_subdomain', add_subdomain, name="add_subdomain"),
    re_path(r'^set_user', set_user, name="set_user"),
    re_path(r'^delet_user', delet_user, name="del_user"),
    re_path(r'^reset_user_2fa', reset_user_2fa, name="reset_user_2fa"),
    re_path(r'^delet_domain', delet_domain, name="delete_domain"),
    re_path(r'^common/', include(('common.urls', 'common'), namespace='common')),
    re_path(r'^ip/update/(?P<domain>.*)/(?P<ip>.*)', set_ip_web),
    re_path(r'^ip/update/', set_ip_web, name="ip_update"),
    re_path(r'^$', main),
)

# Action URLs that should NOT carry a language prefix (they redirect after).
urlpatterns += [
    re_path(r'^impersonate/(?P<user_id>\d+)/start', impersonate, name='impersonate_start'),
    re_path(r'^impersonate/stop', stop_impersonating, name='impersonate_stop'),
]

admin_url = os.environ.get('DJANGO_ADMIN_URL', 'admin')
urlpatterns += [
    re_path(r'^' + admin_url + '/', admin.site.urls),
]
