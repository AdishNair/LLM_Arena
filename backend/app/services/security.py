from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings

# PBKDF2 avoids bcrypt backend edge cases on some Windows/python builds.
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {'sub': subject, 'exp': expires}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
