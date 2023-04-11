
import jwt
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.response import Response
from utils.response_attributes import status_code,messages
from users.models import Users
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from utils.redis_handler import check_redis

def get_tokens_for_user(user):
    #generate token for user
    
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def decodetoken(request):
    JWT_authenticator = JWTAuthentication()
    # authenitcate() verifies and decode the token
    # if token is invalid, it raises an exception and returns 401
    response = JWT_authenticator.authenticate(request)
    print(response)
    if response is not None:
        # unpacking
        user , token = response
        print("this is decoded token claims", token.payload)
    else:
        print("no token is provided in the header or the header is missing")

class JwtTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self,request):
        JWT_authenticator = JWTAuthentication()
        response = JWT_authenticator.authenticate(request)
        JWT_raw_token = str(request.META['HTTP_AUTHORIZATION']).split(' ')
        if not response:
            raise exceptions.AuthenticationFailed('Auth failed')
        # unpacking
        # user , token = response
        #check if token is valid
        # print(JWT_raw_token[1])
        if check_redis(JWT_raw_token[1]):
            return response
        else:
            raise exceptions.AuthenticationFailed('session expired')
