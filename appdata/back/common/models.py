#encoding:utf-8
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib import admin
# Create your models here.


class Activity_log(models.Model):
    id_log=models.AutoField(primary_key=True)
    date=models.DateTimeField(auto_now_add=True)
    username=models.ForeignKey(User, db_column='username', to_field='username', verbose_name='Usuario', on_delete=models.PROTECT, null=True, blank=True, default=None)
    action=models.CharField(max_length=256, verbose_name=u'Action', null=True, blank=True, default=None)
    ip=models.CharField(max_length=4096, verbose_name=u'IP', null=True, blank=True, default=None)
    xforward=models.CharField(max_length=4096, verbose_name=u'IP User', null=True, blank=True, default=None)
    user_affected=models.CharField(max_length=4096, verbose_name=u'User Affected', null=True, blank=True, default=None)
    domain=models.CharField(max_length=1096, verbose_name=u'Domain', null=True, blank=True, default=None)
    agent=models.CharField(max_length=1096, verbose_name=u'Agent', null=True, blank=True, default=None)
    code=models.CharField(max_length=1096, verbose_name=u'Code', null=True, blank=True, default=None)
    result=models.CharField(max_length=4096, verbose_name=u'Result', null=True, blank=True, default=None)

    def __unicode__(self):
        return '%s - %s - %s - %s' % (self.date, self.action, self.user_affected, self.result)

    def __str__(self):
        return '%s - %s - %s - %s' % (self.date, self.action, self.user_affected, self.result)

    class Meta:
        db_table=u'activity_log'
        ordering = ['-id_log']

    class Admin:
        pass

admin.site.register(Activity_log)
