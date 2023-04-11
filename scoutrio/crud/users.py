from django.contrib.auth import get_user_model
from loguru import logger
from utils.response_attributes import status_code,messages
from rest_framework.response import Response

def create_superuser(user_data):
    try:
        user_id = get_user_model().objects.create_superuser(user_data)
        logger.info(messages['superuser_created'])
    except Exception as err:
        logger.info("error triggered :"+str(err))
        logger.info(messages['superuser_not_created'])
        return Response({'code':500 ,'message':status_code['500'],'details':{'message':[messages['data_error']]}})
    return user_id

def create_user(user_data):
    try:
        user_id = get_user_model().objects.create_user(user_data)
        logger.info(messages['user_created'])
    except Exception as err:
        logger.info("error triggered :",err)
        logger.info(messages['user_not_created'])
        return Response({'code':500 ,'message':status_code['500'],'details':{'message':[messages['data_error']]}})
    return user_id