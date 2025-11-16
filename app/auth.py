import re
import logging
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from app.config import settings
from app.models import User
from app.database import get_session

logger = logging.getLogger("pokedex_api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------------------------------
#  VALIDADORES Y UTILIDADES
# -------------------------------------------------
EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")

def get_password_hash(password: str) -> str:
    """Hashea la contraseña."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña con hash bcrypt."""
    return pwd_context.verify(plain, hashed)

def get_user_by_username(session: Session, username: str):
    """Busca un usuario por nombre de usuario."""
    return session.exec(select(User).where(User.username == username)).first()


# -------------------------------------------------
#  CREACIÓN DE TOKENS JWT
# -------------------------------------------------
def create_access_token(username: str, user_id: int, expires_delta: timedelta | None = None) -> str:
    """Crea un token de acceso (1 hora por defecto)."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode = {
        "sub": username,
        "user_id": user_id,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": expire,
    }

    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.info(f"Access token creado para user_id={user_id}")
    return token


def create_refresh_token(username: str, user_id: int, expires_delta: timedelta | None = None) -> str:
    """Crea un token de refresco (7 días por defecto)."""
    expire = datetime.utcnow() + (expires_delta or timedelta(days=7))
    to_encode = {
        "sub": username,
        "user_id": user_id,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": expire,
    }

    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.info(f"Refresh token creado para user_id={user_id}")
    return token


# -------------------------------------------------
#  AUTENTICACIÓN DE PETICIONES
# -------------------------------------------------
def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
):
    """Obtiene el usuario autenticado desde el header Authorization."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(f"AuthError: No token en {request.url.path}")
        raise HTTPException(status_code=401, detail="Token requerido")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")

        if token_type != "access":
            logger.warning(f"AuthError: token no es de tipo 'access' ({request.url.path})")
            raise HTTPException(status_code=401, detail="Tipo de token inválido")

        if user_id is None:
            logger.warning("AuthError: token sin user_id")
            raise HTTPException(status_code=401, detail="Token inválido")

    except JWTError as e:
        logger.warning(f"AuthError JWT: {str(e)} ({request.url.path})")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    # Aquí usamos la sesión inyectada (misma que usa pytest)
    user = session.exec(select(User).where(User.id == user_id)).first()

    if not user:
        logger.warning(f"AuthError: usuario no encontrado ({user_id})")
        raise HTTPException(status_code=401, detail="Usuario no válido")

    request.state.user_id = user.id
    return user
