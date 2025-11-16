from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlmodel import Session, select
from app.database import get_session
from app.models import User
from app.auth import get_current_user
from app.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.auth import (
    EMAIL_RE, PASSWORD_RE,
    get_password_hash, verify_password,
    create_access_token, create_refresh_token
)
from app.rate_limiter import limiter
import logging

logger = logging.getLogger("pokedex_api")

router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------
# POST /register
# ------------------------------
@router.post("/register", status_code=201)
@limiter.limit("5/hour")  # 5 por hora por IP
def register(request: Request, payload: RegisterRequest, session: Session = Depends(get_session)):
    username = payload.username.strip()
    email = payload.email.strip()
    password = payload.password

    # Validaciones extra
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(422, detail="Email inválido")
    if not PASSWORD_RE.fullmatch(password):
        raise HTTPException(422, detail="La contraseña debe tener ≥8 caracteres, 1 mayúscula y 1 número")

    # Comprobación de unicidad
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, detail="Email ya registrado")
    if session.exec(select(User).where(User.username == username)).first():
        raise HTTPException(409, detail="Username ya registrado")

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"Usuario registrado correctamente: {user.username}")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
    }


# ------------------------------
# POST /login
# ------------------------------
@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == body.username)).first()

    if not user or not verify_password(body.password, user.hashed_password):
        logger.warning(f"Intento fallido de login: {body.username}")
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = create_access_token(username=user.username, user_id=user.id)
    refresh_token = create_refresh_token(username=user.username, user_id=user.id)

    logger.info(f"Usuario {user.username} inició sesión correctamente")

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


# ------------------------------
# POST /refresh
# ------------------------------
@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh_token(request: Request, payload: dict = Body(...)):
    from jose import JWTError, jwt
    from app.config import settings

    token = payload.get("refresh_token")
    if not token:
        raise HTTPException(400, detail="refresh_token requerido")

    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Validar tipo de token
        if data.get("type") != "refresh":
            raise HTTPException(401, detail="Token inválido")

        username = data.get("sub")
        user_id = data.get("user_id")
        if not username or not user_id:
            raise HTTPException(401, detail="Token inválido")

    except JWTError as e:
        logger.error(f"Error decodificando refresh_token: {e}")
        raise HTTPException(401, detail="Token inválido o expirado")

    # Generar nuevo access token
    new_access = create_access_token(username=username, user_id=user_id)
    logger.info(f"Refresh token usado correctamente por {username}")

    return TokenResponse(access_token=new_access, refresh_token=None, token_type="bearer")

# ---------------------------------
# GET /me (informacion de usuario)
# ---------------------------------
@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}
