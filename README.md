# PyDDNS
Complete system to create your own dynamic DNS server.

Based on the <b>dprandzioch</b> project: https://github.com/dprandzioch/docker-ddns

PyDDNs is a complete solution, allows you to set up and manage their own dns, compatyble with the dyndns2 protocol, the user can update his ip by web interface or using a compatible client for example ddclient.


apt-get install gettext



Pasos para agregar una nueva traducción:
Verificar si ya existe en la carpeta locale, sino existe crearlo
python manage.py makemessages --locale es

Editar el archivo /locale/XXXX/LC_MESSAGES/django.po
compilarlo con:
python django-admin compilemessages
