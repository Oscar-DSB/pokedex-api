import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User

# === Password hashing ===
pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],  # evita límite de 72 bytes y problemas en Windows
    deprecated="auto",
)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# === JWT ===
security = HTTPBearer()

def _create_token(payload: dict, minutes: int) -> str:
    now = datetime.utcnow()
    to_encode = payload.copy()
    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(username: str, user_id: int) -> str:
    return _create_token({"sub": username, "user_id": user_id}, settings.access_token_expire_minutes)

def create_refresh_token(username: str, user_id: int) -> str:
    return _create_token({"sub": username, "user_id": user_id, "type": "refresh"}, settings.refresh_token_expire_minutes)

def get_user_by_username(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()

async def get_current_user(
    credentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username = payload.get("sub")
        if not username:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = get_user_by_username(session, username)
    if not user:
        raise cred_exc
    return user

# === Validaciones (regex) ===
EMAIL_RE   = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PASSWORD_RE= re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")  # ≥8, 1 mayúscula, 1 número
