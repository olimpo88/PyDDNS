from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    city = models.CharField(max_length=150, blank=True)
    description = models.CharField(max_length=15, blank=True)

class SubDomain(models.Model):
    name = models.CharField(max_length=150, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __unicode__(self):
        return '%s - asignado a  %s' % (self.name, self.user.username)


admin.site.register(SubDomain)

