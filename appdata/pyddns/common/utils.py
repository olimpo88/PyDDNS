from copy import copy, deepcopy
from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import fields
from django.forms.forms import BoundField
from django.forms.models import  ModelChoiceField, ModelMultipleChoiceField
#from django.utils import simplejson
import json as simplejson
from django.utils.safestring import mark_safe
from django.db import models, connection, transaction
from django.db.models import Q

#from models import Adm_clave_tabla

def next_pk(pkname):
	"""
	Metodo que sirve para buscar el proximo PK en caso de necesitar insertar un nuevo registro.
	El metodo buscara en la tabla Adm_clave_tabla por un nuevo registro.
	"""

	cursor = connection.cursor()

	rows = cursor.execute("UPDATE ADM_CLAVE_TABLA SET MAX_CLAVE = MAX_CLAVE + 1 WHERE ID_CLAVE = %s", [pkname.upper()])

	cursor.execute("SELECT MAX_CLAVE FROM ADM_CLAVE_TABLA WHERE ID_CLAVE = %s", [pkname.upper()])
	row = cursor.fetchone()
	transaction.commit_unless_managed()

	return row[0]

def get_extcombo(record):
	json={
		'totalCount':len(record),
		'records': list(record)
	}

	return json

class AbmFunction():

	def __init__(self, form):
		self.pk=form._meta.model._meta.fields[form._meta.model._meta.pk_index()].name
		self.modelo=form._meta.model
		self.tabla=form._meta.model._meta.db_table
		self.form=form
		self.lasterror=''

	def make_action(self, request, action):
		json = {
			'errors': {},
			'data': {},
			'message': '',
			'success': False,
		}
		actions={'next':self.next,
				'prev':self.prev,
				'first':self.first,
				'last':self.last,
				'save':self.save,
				'delete':self.delete}

		obj=actions[action](request)
		if obj:
			json['success'] = True
			json['data'] = obj.get_values()
		else:
			json['errors']['reason']=self.lasterror
			#json['errors']['reason']="Error"
		return json

	def next(self, request):
		obj=False
		q=self.form(request.POST).get_adicional_filter(request)
		if (q):
			q.add((Q(pk__gt=request.POST[self.pk])), q.connector)
		else:
			q=Q(pk__gt=request.POST[self.pk])

		rs=self.modelo.objects.filter(*[q]).order_by(self.pk)[:1]

		if rs:
			obj=rs[0]
		else:
			self.lasterror=('Se ha llegado al final de los datos',)
 		return obj

	def prev(self, request):
		obj=False
		q=self.form(request.POST).get_adicional_filter(request)
		if (q):
			q.add((Q(pk__lt=request.POST[self.pk])), q.connector)
		else:
			q=Q(pk__lt=request.POST[self.pk])

		rs=self.modelo.objects.filter(*[q]).order_by('-'+self.pk)[:1]

		if rs:
			obj=rs[0]
		else:
			self.lasterror=('Se ha llegado al final de los datos',)
 		return obj

	def first(self, request):
		q=self.form(request.POST).get_adicional_filter(request)
		if (q):
			rs=self.modelo.objects.filter(*[q]).order_by(self.pk)[:1]
		else:
			rs=self.modelo.objects.order_by(self.pk)[:1]
		obj=rs[0]
 		return obj

	def last(self, request):
		q=self.form(request.POST).get_adicional_filter(request)
		if (q):
			rs=self.modelo.objects.filter(*[q]).order_by('-'+self.pk)[:1]
		else:
			rs=self.modelo.objects.order_by('-'+self.pk)[:1]
		obj=rs[0]
 		return obj

	def save(self, request):
		obj=False
		rs=False

		if request.POST[self.pk].isdigit():
			rs=self.modelo.objects.filter(pk=request.POST[self.pk])

		if rs:
			if (not request.user.has_perm(self.modelo._meta.app_label+'.change_'+self.tabla)):
				self.lasterror=('No posee permisos para Modificar datos.')
				return obj
			frm=self.form(request.POST, instance=rs[0])
		else:
			if (not request.user.has_perm(self.modelo._meta.app_label+'.add_'+self.tabla)):
				self.lasterror=('No posee permisos para Agregar datos.')
				return obj
			frm=self.form(request.POST.copy())

		if not request.POST[self.pk].isdigit():
			frm.data[self.pk] = next_pk(self.pk)

		if frm.is_valid(): 			
			obj=frm.save()
		else:
			for err in frm.errors:
				self.lasterror='%s: %s' % (err, frm.errors[err])

 		return obj

	def delete(self, request):

		if (not request.user.has_perm(self.modelo._meta.app_label+'.delete_'+self.tabla)):
			self.lasterror=('No posee permisos para Eliminar datos.')
			return False

		obj=self.modelo.objects.get(pk=request.POST[self.pk])
		if obj:
			obj.delete()
			obj = self.prev(request)
 		return obj


class FrmExtAbm(forms.ModelForm):    
	"""
	Clase que extiende al ModelForm nativo de DJango para dotarlo de un metodo donde 
	devuelva el conjunto de campos compatible con la sitaxis de EXTJS
	"""
	_ext_config={
		'width':400,
		'height':200,
		'title':'Titulo del Form'
	}

	def ext_config(self, request):
		"""
		Reimplementar esta funcion en cada modelo cambiando por los valores correctos para c/form.
		"""
		self._ext_config['url']=request.META['PATH_INFO']
		return self._ext_config

	def as_ext(self):
		return mark_safe(simplejson.dumps(self,cls=ExtJSONEncoder, indent=4))

	def get_adicional_filter(self, request):
		"""
		Reimplementar esta funcion en aquellos forms que requieran filtros adicionales.
		Se debera devolver 
		"""
		return False

class ExtModel():
	"""
	Clase para extender los modelos nativos y agregarles funcionalidad extra.
	"""
	def get_values(self):
		"""
		Clase que devuelve un diccionario con los campos y datos del Objeto QuerySet.
		Sirve para formar un JSon con los valores de los datos y devolverlos al navegador.
		"""
		val={}
		for field in self._meta.fields:
			val[field.name]=field.value_to_string(self)
		return val
		

class ExtJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode django forms into ExtJS config objects.
    """

    CHECKBOX_EDITOR = {
        'xtype': 'checkbox'
    }
    COMBO_EDITOR = {
            #'listWidth': 'auto',
            'width': 150,
            'xtype': 'combo',
            #'xtype': 'jsoncombo',
        }
    DATE_EDITOR = {
            'xtype': 'datefield'
        }
    EMAIL_EDITOR = {
        'vtype':'email',
        'xtype': 'textfield'
    }
    NUMBER_EDITOR = {
        'xtype': 'numberfield'
    }
    NULL_EDITOR = {
        'fieldHidden': True,
        'xtype': 'textfield'
    }
    TEXT_EDITOR = {
        'xtype': 'textfield'
    }
    TIME_EDITOR = {
        'xtype': 'timefield'
    }
    URL_EDITOR = {
        'vtype':'url',
        'xtype': 'textfield'
    }

    CHAR_PIXEL_WIDTH = 8

    EXT_DEFAULT_CONFIG = {
        'editor': TEXT_EDITOR
        #'labelWidth': 300,
        #'autoWidth': True,
    }

    DJANGO_EXT_FIELD_TYPES = {
        fields.BooleanField: ["Ext.form.Checkbox", CHECKBOX_EDITOR],
        fields.CharField: ["Ext.form.TextField", TEXT_EDITOR],
        fields.ChoiceField: ["Ext.form.ComboBox", COMBO_EDITOR],
        fields.DateField: ["Ext.form.DateField", DATE_EDITOR],
        fields.DateTimeField: ["Ext.form.DateField", DATE_EDITOR],
        fields.DecimalField: ["Ext.form.NumberField", NUMBER_EDITOR],
        fields.EmailField: ["Ext.form.TextField", EMAIL_EDITOR],
        fields.IntegerField: ["Ext.form.NumberField", NUMBER_EDITOR],
        ModelChoiceField: ["Ext.form.ComboBox", COMBO_EDITOR],
        ModelMultipleChoiceField: ["Ext.form.ComboBox", COMBO_EDITOR],
        fields.MultipleChoiceField: ["Ext.form.ComboBox",COMBO_EDITOR],
        #NullField: ["Ext.form.TextField", NULL_EDITOR],
        fields.NullBooleanField: ["Ext.form.Checkbox", CHECKBOX_EDITOR],
        #BooleanField: ["Ext.form.Checkbox", CHECKBOX_EDITOR],
        fields.SplitDateTimeField: ["Ext.form.DateField", DATE_EDITOR],
        fields.TimeField: ["Ext.form.DateField", TIME_EDITOR],
        fields.URLField: ["Ext.form.TextField", URL_EDITOR],
    }

    EXT_DATE_ALT_FORMATS = 'm/d/Y|n/j/Y|n/j/y|m/j/y|n/d/y|m/j/Y|n/d/Y|m-d-y|m-d-Y|m/d|m-d|md|mdy|mdY|d|Y-m-d'

    EXT_TIME_ALT_FORMATS = 'm/d/Y|m-d-y|m-d-Y|m/d|m-d|d'

    DJANGO_EXT_FIELD_ATTRS = {
        #Key: django field attribute name
        #Value: tuple[0] = ext field attribute name,
        #       tuple[1] = default value
        'choices': ['store', None],
        #'default': ['value', None],
        'fieldset': ['fieldSet', None],
        'help_text': ['helpText', None],
        'initial': ['value', None],
        #'input_formats': ['altFormats', None],
        'label': ['fieldLabel', None],
        'max_length': ['maxLength', None],
        'max_value': ['maxValue', None],
        'min_value': ['minValue', None],
        'name': ['name', None],
        'required': ['allowBlank', False],
        'size': ['width', None],
        'hidden': ['fieldHidden', False],
    }

    def default(self, o, form=None, field_name=None):
        if issubclass(o.__class__, (forms.Form,forms.BaseForm)):
            flds = []

            for name, field in o.fields.items():
                if isinstance(field, dict):
                    field['title'] = name
                else:
                    field.name = name
                cfg = self.default(field, o, name)
                flds.append(cfg)

            return flds
        elif isinstance(o, dict):
            #Fieldset
            default_config = {
                'autoHeight': True,
                'collapsible': True,
                'items': [],
                'labelWidth': 200,
                'title': o['title'],
                'xtype':'fieldset',
            }
            del o['title']

            #Ensure fields are added sorted by position
            for name, field in sorted(o.items()):
                field.name = name
                default_config['items'].append(self.default(field))
            return default_config
        elif issubclass(o.__class__, fields.Field):
            #bf = form and form.is_bound and BoundField(form, o, field_name) or None
            bf = BoundField(form, o, field_name)
            #print field_name , o.__class__

            default_config = {}
            if o.__class__ in self.DJANGO_EXT_FIELD_TYPES:
                default_config.update(self.DJANGO_EXT_FIELD_TYPES[o.__class__][1])
            else:
                default_config.update(self.EXT_DEFAULT_CONFIG['editor'])
            config = deepcopy(default_config)
            if bf:
                config['invalidText']="".join(form[field_name].errors)

            if form and form.is_bound:
                data = bf.data
            else:
                if field_name:
                    data = form.initial.get(field_name, o.initial)
                    if callable(data):
                        data = data()
                else:
                    data = None
            config['value'] = data
            for dj, ext in self.DJANGO_EXT_FIELD_ATTRS.items():
                v = None
                if dj == 'size':
                    v = o.widget.attrs.get(dj, None)
                    if v is not None:
                        if o.__class__ in (fields.DateField, fields.DateTimeField,
                           fields.SplitDateTimeField, fields.TimeField):
                            v += 8
                        #Django's size attribute is the number of characters,
                        #so multiply by the pixel width of a character
                        v = v * self.CHAR_PIXEL_WIDTH
                elif dj == 'hidden':
                    v = o.widget.attrs.get(dj, default_config.get('fieldHidden', ext[1]))
                elif dj == 'name':
                    v = bf and bf.html_name or field_name
                elif dj == 'label':
                    v = bf and bf.label or getattr(o, dj, ext[1])
                elif getattr(o, dj, ext[1]) is None:
                    #print "dj:%s field name:%s"%(dj,field_name)
                    pass
                #elif dj == 'input_formats':
                    #alt_fmts = []
                    ##Strip out the '%'  placeholders
                    #for fmt in getattr(field, dj, ext[1]):
                        #alt_fmts.append(fmt.replace('%', ''))
                    #v = u'|'.join(alt_fmts)
                elif isinstance(ext[1], basestring):
                    v = getattr(o, dj, getattr(field, ext[1]))
                elif ext[0] == 'store':
                    v = {
                        'autoLoad': True,
                        'storeId': o.name,
                        'url': '/csds/ext/rdo/queryset/%s/' % (o.name.lower(),),
                        #'xtype': 'jsonstore',
                    }
                elif dj == 'required':
                    try:
                        v = not getattr(o, dj)
                    except AttributeError :
                        v = ext[1]
                else:
                    v = getattr(o, dj, ext[1])
                if v is not None:
                    if ext[0] == 'name':
                        config[ext[0]] = v
                        config['header'] = v
                    elif ext[0] not in ('name', 'dataIndex', 'fieldLabel', 'header', 'defaultValue'):
                    #elif ext[0] in ('allowBlank', 'listWidth', 'store', 'width'):
                            #if isinstance(v, QuerySetIterator):
                            #    config['editor'][ext[0]] = list(v)
                        config[ext[0]] = v
                        if ext[0] == 'store':
                            #config['url'] = v['url']
                            choices = [(c[0],c[1]) for c in o.choices]
                            config['store'] = choices
                            config['displayField'] = 'display'
                            config['editable'] = False
                            #config['editor']['forceSelection'] = True
                            config['hiddenName'] = o.name
                            #config['lastQuery'] = ''
                            config['mode'] = 'local'
                            config['triggerAction'] = 'all'
                            #config['valueField'] = 'id'

                    elif isinstance(v, unicode):
                        config[ext[0]] = v.encode('utf8')
                    else:
                        config[ext[0]] = v
            return config
        else:
            return super(ExtJSONEncoder, self).default(o)


UNIDADES = (
    '',    
    'UN ', 
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ', 
    'SIETE ',
    'OCHO ', 
    'NUEVE ',
    'DIEZ ', 
    'ONCE ', 
    'DOCE ', 
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '    
)                
DECENAS = (      
    'VENTI',     
    'TREINTA ',  
    'CUARENTA ', 
    'CINCUENTA ',
    'SESENTA ',  
    'SETENTA ',  
    'OCHENTA ',  
    'NOVENTA ',  
    'CIEN '      
)                
CENTENAS = (     
    'CIENTO ',   
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',  
    'SEISCIENTOS ', 
    'SETECIENTOS ', 
    'OCHOCIENTOS ', 
    'NOVECIENTOS '  
)                   
                    
def NumeroALetra(number_in):
                             
    converted = ''                             

    if type(number_in) != 'str':
      number = str(number_in)  
    else:                      
      number = number_in       
                                                          
    number_str=number                                     
                                                          
    try:                                                  
      number_int, number_dec = number_str.split(".")      
    except ValueError:                                    
      number_int = number_str                             
      number_dec = ""                                     

    number_str = number_int.zfill(9)
    millones = number_str[:3]      
    miles = number_str[3:6]        
    cientos = number_str[6:]       

    if(millones):
        if(millones == '001'):
            converted += 'UN MILLON '
        elif(int(millones) > 0):    
            converted += '%sMILLONES ' % __convertNumber(millones)
                                                                 
    if(miles):                                                   
        if(miles == '001'):                                      
            converted += 'MIL '                                  
        elif(int(miles) > 0):                                    
            converted += '%sMIL ' % __convertNumber(miles)       
    if(cientos):                                                 
        if(cientos == '001'):                                    
            converted += 'UN '                                   
        elif(int(cientos) > 0):                                  
            converted += '%s ' % __convertNumber(cientos)        

    if number_dec == "":
      number_dec = "00"
    if (len(number_dec) < 2 ):
      number_dec+='0'        

    converted += 'PESOS CON '+ number_dec + "/100 CENTAVOS"

    return converted
                   
def __convertNumber(n):
    output = ''

    if(n == '100'):
        output = "CIEN "
    elif(n[0] != '0'):
        output = CENTENAS[int(n[0])-1]

    k = int(n[1:])
    if(k <= 20):
        output += UNIDADES[k]
    else:
        if((k > 30) & (n[2] != '0')):
            output += '%sY %s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])

    return output



def getForwardedFor(request):
    FORWARDED_FOR_FIELDS = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_HOST',
        'HTTP_X_FORWARDED_SERVER',
    ]
    res=request.META['REMOTE_ADDR']
    for field in FORWARDED_FOR_FIELDS:
        if field in request.META:
            res=res+' '+request.META[field]
    return res
