import secrets
import string
from django.core.signing import TimestampSigner, BadSignature
from scoutrio import env
# Instantiate the signer with the SECRET_KEY
signer = TimestampSigner(salt=env.ENCRYPTION_SALT)#1024bit

random_otp = lambda count:''.join(secrets.choice(string.digits) for i in range(count))

def encrypt_payload(payload:dict) -> str:
    encrypted_string = signer.sign_object(payload)
    return encrypted_string

def decrypt_payload(payload:str) -> dict:
    try:
        decrypted_string = signer.unsign_object(payload,max_age=env.ENCRYPTION_TTL_SECONDS)# token should be only 1 minute old
    except BadSignature:
        decrypted_string = None
    return decrypted_string
