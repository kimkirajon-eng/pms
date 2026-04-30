import bcrypt
from datetime import datetime, timedelta
from jose import jwt

# Ayarlar
SECRET_KEY = "pms_cok_gizli_anahtar_123" 
ALGORITHM = "HS256"

def get_password_hash(password: str):
    """Şifreyi doğrudan bcrypt kullanarak güvenli hale getirir"""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    """Şifreleri doğrudan bcrypt ile karşılaştırır"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
