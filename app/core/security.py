from datetime import datetime, timedelta, timezone  
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Takes a plain-text password and returns a secure, encrypted Bcrypt hash.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Compares a plain-text password with a stored hash to check if they match.
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
        """
        Generates a secure JSON Web Token (JWT) for user session management.
        """
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        
        to_encode = {"exp": expire, "sub": str(subject)}
        
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt