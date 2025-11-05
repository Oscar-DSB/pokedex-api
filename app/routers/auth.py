from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from app.database import get_session
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.auth import (
    EMAIL_RE, PASSWORD_RE,
    get_password_hash, verify_password,
    get_user_by_username,
    create_access_token, create_refresh_token,
)
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# --- POST /register ---
@router.post("/register", status_code=201)
@limiter.limit("5/hour")   # 5/h por IP
def register(request: Request ,payload: RegisterRequest, session: Session = Depends(get_session)):
    username = payload.username.strip()
    email    = payload.email.strip()
    password = payload.password

    # validaciones extra (además de Pydantic)
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(422, "Email inválido")
    if not PASSWORD_RE.fullmatch(password):
        raise HTTPException(422, "La contraseña debe tener ≥8 caracteres, 1 mayúscula y 1 número")

    # unicidad
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "Email ya registrado")
    if session.exec(select(User).where(User.username == username)).first():
        raise HTTPException(409, "Username ya registrado")

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
    }
# --- POST /login ---
@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")   # 10/min por IP
def login(request: Request,payload: LoginRequest, session: Session = Depends(get_session)):
    user = get_user_by_username(session, payload.username.strip())
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos")

    access  = create_access_token(username=user.username, user_id=user.id)
    refresh = create_refresh_token(username=user.username, user_id=user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)

# --- POST /refresh (bonus) ---
@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh_token(request: Request,payload: dict):
    from jose import JWTError, jwt
    from app.config import settings

    token = payload.get("refresh_token")
    if not token:
        raise HTTPException(400, "refresh_token requerido")

    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if data.get("type") != "refresh":
            raise HTTPException(401, "Token inválido")
        username = data.get("sub")
        user_id  = data.get("user_id")
        if not username or not user_id:
            raise HTTPException(401, "Token inválido")
    except JWTError:
        raise HTTPException(401, "Token inválido")

    new_access = create_access_token(username=username, user_id=user_id)
    return TokenResponse(access_token=new_access, refresh_token=None)
