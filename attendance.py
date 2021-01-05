from jose import jwt
import datetime
from models import BlacklistToken


# This method will work as jwt encoding to generate JWT token for attendance
def generate_attendance_code(course_id, time_in_minutes, secret_key='None'):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=time_in_minutes),
            'iat': datetime.datetime.utcnow(),
            'course_id': course_id
        }
        return jwt.encode(
            payload,
            secret_key,
            algorithm='HS256'
        )
    except Exception as e:
        return e


def verify_attendance_code(secret_key, attendance_token):
    try:
        payload = jwt.decode(attendance_token, secret_key)
        
        is_blacklisted_token = BlacklistToken.check_blacklist(attendance_token)
        if is_blacklisted_token:
            return 'Token blacklisted. Please ask teacher to generate new one'
        else:
            return payload
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please ask teacher to generate new one'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please ask teacher to generate new one'

