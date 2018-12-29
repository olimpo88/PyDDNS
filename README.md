# PyDDNS
Complete system to create your own dynamic DNS server.

Based on the <b>dprandzioch</b> project: https://github.com/dprandzioch/docker-ddns


### Description
PyDDNs is a complete solution, allows you to set up and manage their own dns, compatible with the dyndns2 protocol, the user can update his ip by web interface or using a compatible client for example ddclient.

### Video
Watch the video --> [Youtube](https://www.youtube.com/watch?v=L9ORq4zVjec)


### Screenshots
![screenshots](https://i.imgur.com/6HTwrfn.png)


### Run
- Install docker and docker-compose
- Copy the file docker-compose: `cp docker-compose-demo.yml docker-compose.yml`
- Start with command: `docker-compose up`


### Configuration of environment variables
```
    DNS_HOST: ddns  <-- DNS docker name
    DNS_API_PORT: 8080  <-- Port to connect with the API-REST of dprandzioch
    DNS_DOMAIN: ddns.demo.com  <-- our domain
    DNS_SHARED_SECRET: el@sadsadyS58 <-- same password that was set in API-REST of dprandzioch
    DNS_ALLOW_AGENT: ddclient3,ddclient <-- If you want to control by client, put their names separated by comma
    DB_HOST: postgres  <-- postgres docker name
    DB_NAME: pyddns  <-- DB postgres
    DB_USER: pyddns  <-- User postgres
    DB_PASSWORD: PyDyn@m1cDNSP0s <-- Password of user postgres
    DJANGO_ADMIN_URL: administrator  <-- URL to enter the django administration
    DJANGO_SU_NAME: admin  <--- Default administrator user
    DJANGO_SU_EMAIL: admin@my.company  <-- Email to default administrator
    DJANGO_SU_PASSWORD: 1234  <-- Password to default administrator
    OWN_ADMIN: 1  <-- 1 = all users can create subdomains, 0 = only the administrator can create subdomains
```

### Architecture
![screenshots](https://i.imgur.com/KWZzxOs.png)

### DDNS clients
You can use any client compatible with the DynDNS2 protocol.

###### For Windows
I recommend using `DynDNS Simply Client`, you can download it here: https://sourceforge.net/projects/dyndnssimplycl/


###### For Linux and Mac OS X
I recommend using `ddclient`, basic configuration:
```
protocol=dyndns2
use=web, web=checkip.dyndns.com, web-skip='IP Address'
server=localhost.com
login=userdemo
password='userpassword'
yourdomain.ddns.demo.com
```


### Translation :us::es:
The system automatically detects the language of your browser.
If you want to add your translations you must follow the following steps:

1. Enter the container console: `docker-compose exec python bash`
2. You must execute the following command, replacing the last attribute: `python manage.py makemessages --locale es`
3. Edit the file: `appdata/pyddns/locale/XXXX/LC_MESSAGES/django.po`
4. Once the translations are finished, it must be compiled: `python manage.py compilemessages`

### Contact :email:
https://www.linkedin.com/in/peraltaleandro/
