
import pytz
import json
from datetime import datetime,timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from loguru import logger
from django.contrib.auth import get_user_model
from .serializers import RegisterSeriailzer,LoginSerializer,LoginLogSerializer,ReadMyDetailsSerializer,LoginLogoutLogSerializer
from utils.validations import validate_phone_number,validate_name,validate_dob
from utils.country_code import ph_country_code
from utils.response_attributes import status_code,messages
from utils.generative_strings import random_otp,encrypt_payload,decrypt_payload
from utils.redis_handler import insert_redis,get_redis,delete_redis,get_ttl_redis
from email_validator import validate_email,EmailNotValidError
from users.models import Users,login_log
from scoutrio.crud.users import create_superuser,create_user
from utils.jwt_handler import get_tokens_for_user,decodetoken,JwtTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from scoutrio import env
#from django.contrib.auth import authenticate

tz = pytz.timezone('UTC')  

# Create your views here.
class RegisterViewSet(viewsets.ModelViewSet):
    serializer_class = RegisterSeriailzer
    def create(self, request, *args, **kwargs):
        parameters = request.data
        ph = ph_country_code['India']+parameters.get("ph")
        email = parameters.get("email")
        first_name = parameters.get("first_name")
        last_name = parameters.get("last_name")
        dob = parameters.get("dob")
        is_superuser = bool(parameters.get("is_superuser"))
        user_insert={}
        #ph-validation
        ph_check = Users.objects.filter(ph = ph)
        if ph_check :
            return Response({'code':409,'message':status_code['409'],'details':{'message':[messages['ph_exist']]}})
        if not validate_phone_number(ph):
            return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['ph_invalid']]}})
        user_insert['ph'] =  ph

        #email-validation
        if email:
            email_check = get_user_model().objects.filter(email = email)
            if email_check :
                return Response({'code':409,'message':status_code['409'],'details':{'message':[messages['email_exist']]}})
            try:
                validation = validate_email(email, check_deliverability=False)
                email = validation.email
            except EmailNotValidError as e:
                return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['email_invalid']]}})
        user_insert['email'] =  email
        #firstname-validation
        if not validate_name(first_name):
            return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['name_invalid']]}})
        user_insert['first_name'] = first_name

        #last_name-validation
        if last_name:
            if not validate_name(last_name):
                return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['name_invalid']]}})
        user_insert['last_name'] = last_name

        #dob-validation
        if not dob:
            return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['dob_invalid']]}})
        else:
            dob = validate_dob(dob)
            if dob == "underage":
                return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['dob_underage']]}})
            elif dob == False:
                return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['dob_invalid']]}})
        
        user_insert['dob'] = dob
        if is_superuser == True:
            user_insert['is_superuser'] = is_superuser
            user_id = create_superuser(user_insert)            
        else:
            user_id = create_user(user_insert)

        return Response({
            "code":201,
            'message':status_code['201'],
            'details':{
                'message':[messages['user_created']],
                'user_id':str(user_id)
            }
        })


#send otp after and number is enterd
class ProcessLoginOTP(viewsets.ModelViewSet):
    serializer_class = LoginLogSerializer
    queryset = ()
    http_method_names = ['post']
    def create(self, request, *args, **kwargs):
        parameters = request.data
        ph = ph_country_code['India']+parameters.get("ph")
        
        if not ph:
            return Response({'code':404,'message':status_code['404'],'details':{'message':[messages['ph_not_found']]}})
        else:
            try:
                db_user = Users.objects.get(ph = ph)
            except Exception as ex:
                logger.error(str(ex))
                return Response({'code':404,'message':status_code['404'],'details':{'message':[messages['ph_not_found']]}})
            #create only three otp in one minute to reduce bruteforce attack
            log_data =  login_log.objects.filter(user = db_user).order_by('-created_on')[:5]
            count = 0
            for i in log_data:
                time_difference = datetime.now().astimezone(tz)-i.created_on.astimezone(tz)
                if time_difference<timedelta(minutes=1):
                    if count >=2: 
                        return Response({'code':429,'message':status_code['429'],'details':{'message':[messages['maximum_request']]}})
                    count +=1
            otp = random_otp(env.OTP_DIGITS)
            #save otp as password
            db_user.set_password(otp)
            db_user.save()
            #encrypt otp and save in password generated log
            payload = {
                'ph':db_user.ph,
                'dob':str(db_user.dob),
                'otp':otp,
                'doc':str(db_user.created_at),
                'current_date':str(datetime.now()),
                'id':db_user.id,
            }
            token = encrypt_payload(payload)
            serializer_data = {
                'user':db_user.id,
                'otp':otp,
                'token':token,
                'is_verified':False
            }
            serializer = self.get_serializer(data=serializer_data)
            if serializer.is_valid():
                serializer.save()
                #send otp as celery task
                print(otp)
                return Response({'code':201,'message':status_code['201'],'details':messages['otp_created'],'data':{'token':serializer.data['token']}})
            else:
                return Response({'code':422,'message':status_code['422'],'details':messages['otp_failed'],'data':serializer.errors})# status=status.HTTP_400_BAD_REQUEST)

class LoginViewSet(viewsets.ModelViewSet):
    serializer_class = LoginSerializer
    queryset = ()
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        parameters = request.data
        token = parameters.get("token")
        otp = parameters.get("otp")
        
        if not token or not otp:
            logger.warning("Token verification failed")
            return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['wrong_credentials']]}})

        #decrypt token
        decrypt_log = decrypt_payload(token)
        if not decrypt_log or otp != decrypt_log.get('otp'):
            logger.warning("Token verification failed")
            return Response({'code':422,'message':status_code['422'],'details':{'message':[messages['otp_invalid']]}})
        logger.info("Token verification Successfull")
        #update in login log
        db_user = Users.objects.filter(id=decrypt_log.get('id')).first()
        if not db_user:
            logger.error("No Users found")
            return Response({'code':404,'message':status_code['404'],'details':{'message':[messages['user_not_found']]}})
        
        if not db_user.check_password(decrypt_log.get('otp')):
            logger.warning("Couldnt authetnticate ")
            return Response({'code':401,'message':status_code['401'],'details':{'message':[messages['wrong_credentials']]}})
        logger.info("User authentication Successfull")
        #redis data insertion
        user_data = db_user.__dict__
        redis_user_data = str({
            'id':user_data['id'],
            'is_superuser':user_data['is_superuser'],
            'ph':user_data['ph'],
            'email':user_data['email'],
            'first_name':user_data['first_name'],
            'last_name':user_data['last_name'],
            'dob':user_data['dob'].strftime('%d/%m/%Y'),
            'is_active':user_data['is_active'],
            'is_verified':user_data['is_verified'],
            'is_deactive':user_data['is_deactive'],
            'is_premium':user_data['is_premium'],
            })
        token = get_tokens_for_user(db_user)
        insert_redis(token['access'],redis_user_data,expiry=env.JWT_TTL_SECONDS)
        logger.info("User inserted in redis")
        serializer_data = {
            'user':user_data['id'],
            'access_token':token['access'],
            'logged_in':True,
            'logged_out':False,
        }
        serializer = LoginLogoutLogSerializer(data=serializer_data)
        if serializer.is_valid():
            serializer.save()  
            logger.info("Login log created")
        response = Response()
        response.data = {
            'jwt':token
        }
        return response

class LogoutViewSet(viewsets.ModelViewSet):
    permission_classes = ()
    authentication_classes = [JwtTokenAuthentication]#JWTAuthentication
    permission_classes = [IsAuthenticated]
    serializer_class = LoginLogoutLogSerializer#create log
    http_method_names = ['post']

    def create(self,request):
        JWT_raw_token = str(request.META['HTTP_AUTHORIZATION']).split(' ')[1]
        redis_user = get_redis(JWT_raw_token,decode_dict=True)
        if delete_redis(JWT_raw_token):
            serializer_data = {
            'user':redis_user['id'],
            'access_token':JWT_raw_token,
            'logged_in':False,
            'logged_out':True,
            }
            serializer = self.get_serializer(data=serializer_data)
            if serializer.is_valid():
                serializer.save()
                logger.info('Redis token removed and log created')
            return Response({'code':204 ,'message':status_code['200'],'data':messages['logout']})
        else:
            return Response({'code':422,'message':status_code['422'],'data':messages['logout_failed']})
            

class MyDetails(viewsets.ModelViewSet):
    permission_classes = ()
    authentication_classes = [JwtTokenAuthentication]##JWTAuthentication
    permission_classes = [IsAuthenticated]#
    serializer_class = ReadMyDetailsSerializer
    http_method_names = ['get','put','delete']

    
    
    def list(self, request, *args, **kwargs):
        #getdata from db directly
        #db_user = request.user
        JWT_raw_token = str(request.META['HTTP_AUTHORIZATION']).split(' ')[1]
        redis_user_data = get_redis(JWT_raw_token,decode_dict=True)
        return Response({'code':200,'message':status_code['200'],'data':redis_user_data})
    
    def update(self, request, *args, **kwargs):
        form_data = request.data
        JWT_raw_token = str(request.META['HTTP_AUTHORIZATION']).split(' ')[1]
        redis_user_data = get_redis(JWT_raw_token,decode_dict=True)
        
        #if email isnt verified dont given an option to update email
        if redis_user_data['is_verified']:
            logger.info('User has the permission to update email')
            email_check = Users.objects.filter(email=form_data['email'])#email should be verified again
            #print(email_check)
            if not email_check :
                db_user = Users.objects.get(id=redis_user_data['id'])
                db_user.email=form_data['email']
                db_user.first_name=form_data['first_name']
                db_user.last_name=form_data['last_name']
                #db_user.is_active=form_data['is_active']#turnning is_active to false forces user to logout the jwt
                db_user.is_verified=False
                db_user.save()
                logger.info('User details updated')
                #updating redis cache with updated data
                remaining=get_ttl_redis(JWT_raw_token)
                if remaining:
                    redis_user_data = str({
                    'id':redis_user_data['id'],
                    'is_superuser':db_user.is_superuser,
                    'ph':db_user.ph,
                    'email':form_data['email'],
                    'first_name':form_data['first_name'],
                    'last_name':form_data['last_name'],
                    'dob':db_user.dob.strftime('%d/%m/%Y'),
                    'is_active':db_user.is_active,
                    'is_verified':False,
                    'is_deactive':db_user.is_deactive,
                    'is_premium':db_user.is_premium,
                    })
                    insert_redis(JWT_raw_token,redis_user_data,expiry=remaining)
                    logger.info('User details updated in redis')
            else:
                return Response({'code':409,'message':status_code['409'],'message':messages['email_not_avilable']})
        else:
            logger.info('User has no permission to update email')
            db_user = Users.objects.get(id=redis_user_data['id'])
            db_user.first_name=form_data['first_name']
            db_user.last_name=form_data['last_name']
            #db_user.is_active=form_data['is_active']#turnning is_active to false forces user to logout the jwt
            db_user.save()
            logger.info('User details updated')
            #updating redis cache with updated data
            remaining=get_ttl_redis(JWT_raw_token)
            if remaining:
                    redis_user_data = str({
                    'id':redis_user_data['id'],
                    'is_superuser':db_user.is_superuser,
                    'ph':db_user.ph,
                    'email':db_user.email,
                    'first_name':form_data['first_name'],
                    'last_name':form_data['last_name'],
                    'dob':db_user.dob.strftime('%d/%m/%Y'),
                    'is_active':db_user.is_active,
                    'is_verified':db_user.is_verified,
                    'is_deactive':db_user.is_deactive,
                    'is_premium':db_user.is_premium,
                    })
                    insert_redis(JWT_raw_token,redis_user_data,expiry=remaining)
                    logger.info('User details updated in redis')
            #update redis
        return Response({'code':200,'message':status_code['200'],'data':''})

    def delete(self, request, *args, **kwargs):
        query_parameters = request.query_params
        form_data = request.data
        
        JWT_raw_token = str(request.META['HTTP_AUTHORIZATION']).split(' ')[1]
        redis_user = get_redis(JWT_raw_token,decode_dict=True)
        db_user = Users.objects.get(id=redis_user['id'])
        if query_parameters.get('delete'):#soft delete user|cant be retrieved
            db_user.is_active = form_data['status']
            db_user.save()
            delete_redis(JWT_raw_token)
        if query_parameters.get('activate'):#activation and deeactivation of account by user
            db_user.is_deactive = form_data['status']
            db_user.save()        
        return Response({'code':200,'message':status_code['200'],'data':''})