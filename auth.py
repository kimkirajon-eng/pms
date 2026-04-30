from passlib.context import CryptContext
from datetime import datetime, timedelta
import json
import base64
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Şifre hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key (Render'da env variable olarak ayarlanacak)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

def hash_password(password: str) -> str:
    """Şifreyi hashle"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi doğrula"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """JWT tarzı token oluştur (basit versiyonu)"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire.timestamp()})
    
    # Basit JWT implementasyonu
    payload = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode()
    signature = base64.urlsafe_b64encode(
        hmac.new(
            SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256
        ).digest()
    ).decode()
    
    return f"{payload}.{signature}"

def verify_token(token: str) -> dict:
    """Token'ı doğrula ve payload'u döndür"""
    try:
        if not token:
            return None
        
        payload, signature = token.rsplit(".", 1)
        
        # Signature kontrol et
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(
                SECRET_KEY.encode(),
                payload.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        if signature != expected_signature:
            return None
        
        # Payload decode et
        decoded = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded)
        
        # Token süresi kontrol et
        if data.get("exp") < datetime.utcnow().timestamp():
            return None
        
        return data
    except Exception:
        return None
