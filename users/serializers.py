from rest_framework import serializers
from .models import Users,login_log,login_logout_log


class RegisterSeriailzer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('ph','email','first_name','last_name','dob')

class LoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = login_log
        fields = ['user','otp','token','is_verified']
        # read_only_fields = ['otp']

class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ('ph')

class ReadMyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['email','first_name','last_name','is_active']
        read_only_fields = fields


class LoginLogoutLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = login_logout_log
        fields = ['user','access_token','logged_in','logged_out']