#encoding:utf-8
from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib import admin
# Create your models here.


class Activity_log(models.Model):
    id_log=models.AutoField(primary_key=True)
    fecha_hora=models.DateTimeField(auto_now_add=True)
    username=models.ForeignKey(User, db_column='username', to_field='username', verbose_name='Usuario', on_delete=models.PROTECT, null=True, blank=True, default=None)
    action=models.CharField(max_length=256, verbose_name=u'Acción', null=True, blank=True, default=None)
    origen=models.CharField(max_length=4096, verbose_name=u'Origen', null=True, blank=True, default=None)
    ip_origen=models.CharField(max_length=4096, verbose_name=u'IP Origen', null=True, blank=True, default=None)
    afectado=models.CharField(max_length=4096, verbose_name=u'Afectado', null=True, blank=True, default=None)
    dominio=models.CharField(max_length=1096, verbose_name=u'Dominio', null=True, blank=True, default=None)
    agente=models.CharField(max_length=1096, verbose_name=u'Agente', null=True, blank=True, default=None)
    codigo=models.CharField(max_length=1096, verbose_name=u'Codigo', null=True, blank=True, default=None)
    resultado=models.CharField(max_length=4096, verbose_name=u'Resultado', null=True, blank=True, default=None)

    def __unicode__(self):
	return '%s - %s - %s -%s' % (self.fecha_hora, self.action, self.afectado[:40], self.resultado[:40])

    def __str__(self):
	return '%s - %s - %s - %s' % (self.fecha_hora, self.action, self.afectado[:40], self.resultado[:40])

    class Meta:
	db_table=u'activity_log'
	ordering = ['-id_log']

    class Admin:
	pass

admin.site.register(Activity_log)