from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
import uuid


#user creation helper ->https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#abstractbaseuser
#Custom user manager
class UsersManager(BaseUserManager):
    use_in_migrations = True
    
    def create_user(self, validated_data):
        if not validated_data.get("ph"):
            raise ValueError("ph required")
        user = self.model(
            ph = validated_data.get("ph",""),
            email = validated_data.get("email",""),
            first_name = validated_data.get("first_name",""),
            last_name = validated_data.get("last_name",""),
            dob = validated_data.get("dob","")
        )
        #dynamic password creation
        # dynamic_password = str(uuid.uuid4())
        # user.set_password(dynamic_password)
        user.save()
        return user   

    def create_superuser(self,validated_data):
        role_id = ""
        if not validated_data.get("ph"):
            raise ValueError("ph required")
        superuser = self.model(
            ph = validated_data.get("ph",""),
            email = validated_data.get("email",""),
            first_name = validated_data.get("first_name",""),
            last_name = validated_data.get("last_name",""),
            dob = validated_data.get("dob","")
        )
        if validated_data.get("is_superuser"):
            superuser.is_superuser = True
        else:
            superuser.is_superuser = False
        superuser.save()
        return superuser
        
#Custom user
class Users(AbstractBaseUser,PermissionsMixin):
    
    ph =  models.CharField(max_length = 50, blank=False, unique=True)
    email = models.EmailField(blank=True)#email uniquenes should be checked manually
    password = models.CharField(max_length=500,null=False)
    first_name = models.CharField(max_length = 100, blank=False)
    last_name = models.CharField(max_length = 100, blank=True, null=True)
    dob = models.DateTimeField(blank=False)
    created_at = models.DateTimeField(auto_now_add=timezone.now) #auto_now=True: This option sets the field's value to the current date and time every time the object is saved to the database. This means that the value will be updated every time the object is modified and saved.
    verified_at = models.DateTimeField(blank=True,null=True)
    is_active = models.BooleanField(default=True,help_text="wether user is deleted beyond recovery.if user deleted, flag is True| if user not deleted, flag is false")
    is_verified = models.BooleanField(default=False,help_text="wether user is verified by email.")
    is_deactive = models.BooleanField(default=False,help_text="wether user account is deactivated.if is_deactive is true,user is deactivated|if is_deactive is false user is active")
    is_premium = models.BooleanField(default=False,help_text="wether user is in a premium plan.")
    premium = models.CharField(max_length = 50, blank=True, null = True)

    objects = UsersManager()

    USERNAME_FIELD = "ph"

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def get_full_name(self):
        '''
        Returns the first_name plus the last_name, with a space in between.
        '''
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()
    
    def get_ph(self):
        '''
        Returns the phone number of the user.
        '''
        return self.ph
    
    def get_email(self):
        '''
        Returns the phone number of the user.
        '''
        return self.ph
    
class login_log(models.Model):
    user = models.ForeignKey(Users,on_delete=models.CASCADE,null=False,blank=False)
    otp = models.CharField(max_length=10,null=False,default="")
    token = models.CharField(max_length=512,null=False,default="")
    is_verified = models.BooleanField(default=False)#logged in
    created_on = models.DateTimeField(auto_now_add=timezone.now)
    updated_on = models.DateTimeField(auto_now=True)

class login_logout_log(models.Model):
    user = models.ForeignKey(Users,on_delete=models.CASCADE,null=False,blank=False)
    access_token = models.CharField(max_length=512,null=False,default="")
    logged_in = models.BooleanField(default=False)#logged in
    logged_out = models.BooleanField(default=False)#logged out
    created_on = models.DateTimeField(auto_now_add=timezone.now)