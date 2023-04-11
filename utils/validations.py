import re
from datetime import datetime

def validate_phone_number(number):
    pattern = re.compile(r'^\+91[1-9][0-9]{9}$')
    return pattern.match(number) is not None

def validate_name(name):
    if name.isalpha():
        return name.title()
    else:
        return False

def validate_dob(dob,format='%Y-%m-%d'):
    try:
        difference = datetime.now() - datetime.strptime(dob, format)
        years = difference.days // 365.2425#avg days in a year
        if years >= 18:
            return dob
        else:
            return "underage"
    except ValueError:
        return False