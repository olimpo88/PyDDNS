from django.conf.urls import url, include
from common.views import *

urlpatterns = [
    url(r'^logout/', logout, name="logout"),
    url(r'^login/', login, name="login"),
    url(r'^dologin/', dologin, name="dologin"),
    url(r'^permission_denied', permission_denied, name="permission_denied"),
    url(r'^sin_permiso', sin_permiso, name="sin_permiso"),
    url(r'^$', login, name="login"),
]


