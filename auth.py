from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

# Şifreleme ayarları
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "pms_cok_gizli_anahtar_123" 
ALGORITHM = "HS256"

def get_password_hash(password):
    """Şifreyi güvenli hale getirir (Hashleme)"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """Şifreleri karşılaştırır"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """Giriş anahtarı (Token) oluşturur"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    """Token doğrulaması yapar"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None
