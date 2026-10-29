from django.contrib.admin.apps import AdminConfig


class PyDDNSAdminConfig(AdminConfig):
    """Use SecureAdminSite as ``admin.site`` (see common/admin_site.py)."""
    default_site = 'common.admin_site.SecureAdminSite'
