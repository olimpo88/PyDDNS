from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.urls import reverse_lazy

from common.views import *
from common import views_2fa

urlpatterns = [
    re_path(r'^logout/', logout, name="logout"),
    re_path(r'^login/', login, name="login"),
    re_path(r'^dologin/', dologin, name="dologin"),
    re_path(r'^verify2fa/', verify2fa, name="verify2fa"),
    path('2fa/', views_2fa.index, name='twofactor'),
    path('2fa/setup/', views_2fa.setup, name='twofactor_setup'),
    path('2fa/codes/', views_2fa.codes, name='twofactor_codes'),
    path('2fa/disable/', views_2fa.disable, name='twofactor_disable'),
    path('2fa/regenerate/', views_2fa.regenerate, name='twofactor_regenerate'),
    re_path(r'^permission_denied', permission_denied, name="permission_denied"),
    re_path(r'^sin_permiso', sin_permiso, name="sin_permiso"),
]

# Password-reset flow — only registered when self-service is enabled.
# Operators that prefer admin-controlled credentials should set
# ALLOW_PASSWORD_RESET=0; the URLs return 404 and the "Forgot password?"
# link disappears from the login page.
if getattr(settings, 'ALLOW_PASSWORD_RESET', True):
    urlpatterns += [
        path(
            'password_reset/',
            auth_views.PasswordResetView.as_view(
                template_name='password_reset/form.html',
                email_template_name='password_reset/email.txt',
                html_email_template_name='password_reset/email.html',
                subject_template_name='password_reset/subject.txt',
                success_url=reverse_lazy('common:password_reset_done'),
            ),
            name='password_reset',
        ),
        path(
            'password_reset/done/',
            auth_views.PasswordResetDoneView.as_view(
                template_name='password_reset/done.html',
            ),
            name='password_reset_done',
        ),
        path(
            'reset/<uidb64>/<token>/',
            auth_views.PasswordResetConfirmView.as_view(
                template_name='password_reset/confirm.html',
                success_url=reverse_lazy('common:password_reset_complete'),
            ),
            name='password_reset_confirm',
        ),
        path(
            'reset/done/',
            auth_views.PasswordResetCompleteView.as_view(
                template_name='password_reset/complete.html',
            ),
            name='password_reset_complete',
        ),
    ]

urlpatterns += [
    re_path(r'^$', login),
]
