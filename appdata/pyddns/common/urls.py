from django.conf.urls import url, include
from common.views import *

urlpatterns = [
    url(r'^logout/', logout),
    url(r'^login/', login),
    url(r'^dologin/', dologin),
    url(r'^sin_permiso', sin_permiso),
    url(r'^$', login),
]


