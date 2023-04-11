import redis
import json
from scoutrio import env

conn = redis.Redis(
    host=env.REDIS_HOST,
    port=env.REDIS_PORT,
    db=env.REDIS_DB,
    #password='foobared',
    decode_responses=True,
)

def insert_redis(key:str,value:str=None,expiry=None,keepttl=False):
    #Note datetime objects are not json serializabe so convert it inot format and insert
    if keepttl:
        return conn.set(key,value,keepttl=keepttl)
    return conn.set(key,value,ex=expiry)

def check_redis(key:str):
    if conn.get(key) is None:
        return False
    else:
        return True

def get_redis(key:str,decode_dict=None):
    #Note datetime objects are not json serializabe so convert it inot format and insert
    data = conn.get(key)
    if decode_dict == True:
        #converting string to dict
        data = data.replace("'", "\"").replace("False", "false").replace("True", "true")
        return json.loads(data)
    return data

def delete_redis(key:str):
    if check_redis(key):
        conn.delete(key)
        return True
    else: 
        return False
    
def get_ttl_redis(key:str):
    if check_redis(key):
        return conn.ttl(key)
    else: 
        return False