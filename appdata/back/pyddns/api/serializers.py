from rest_framework import serializers
from pyddns.models import SubDomain

class SubDomainSerializer(serializers.ModelSerializer):
	class Meta:
		model=SubDomain
		fields=('name','user')