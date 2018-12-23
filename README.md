# PyDDNS
Complete system to create your own dynamic DNS server.

Based on the <b>dprandzioch</b> project: https://github.com/dprandzioch/docker-ddns

### Description
PyDDNs is a complete solution, allows you to set up and manage their own dns, compatyble with the dyndns2 protocol, the user can update his ip by web interface or using a compatible client for example ddclient.


### Translation :us::es:
The system automatically detects the language of your browser.
If you want to add your translations you must follow the following steps:

1. Enter the container console: **docker-compose exec python bash**
2. Check if the folder of your language exists, for example: **appdata/pyddns/locale/es**
3. if the folder exist go to point **4**,  if the folder does not exist you must execute the following command, replacing the last attribute: **python manage.py makemessages --locale es**
4. Edit the file **appdata/pyddns/locale/XXXX/LC_MESSAGES/django.po**
5. Once the translations are finished, it must be compiled: **python manage.py compilemessages**
