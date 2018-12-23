# PyDDNS
Complete system to create your own dynamic DNS server.

Based on the <b>dprandzioch</b> project: https://github.com/dprandzioch/docker-ddns

### Description
PyDDNs is a complete solution, allows you to set up and manage their own dns, compatyble with the dyndns2 protocol, the user can update his ip by web interface or using a compatible client for example ddclient.


### Translation :us::es:
The system automatically detects the language of your browser.
If you want to add your translations you must follow the following steps:

1. Enter the container console: **docker-compose exec python bash**
2. You must execute the following command, replacing the last attribute: **python manage.py makemessages --locale es**
3. Edit the file **appdata/pyddns/locale/XXXX/LC_MESSAGES/django.po**
4. Once the translations are finished, it must be compiled: **python manage.py compilemessages**
