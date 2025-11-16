from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, conint, conlist


class UserBase(BaseModel):
    """Campos comunes del usuario"""
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=50)


class UserCreate(UserBase):
    """Esquema para registrar un nuevo usuario"""
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    """Datos que se devuelven al consultar un usuario"""
    id: int
    created_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    pokemon_ids: Optional[List[int]] = Field(default_factory=list)

class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    pokemon_ids: Optional[conlist(int, min_length=1, max_length=6)] = None

class TeamMemberOut(BaseModel):
    pokemon_id: int
    pokemon_name: Optional[str] = None


class TeamOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    members: List[TeamMemberOut]
    model_config = ConfigDict(from_attributes=True)

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    password: str = Field(min_length=8, max_length=128)  # política se valida extra en auth

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class PokedexCreate(BaseModel):
    pokemon_id: conint(gt=0)
    nickname: Optional[str] = None
    is_captured: bool = True

class PokedexUpdate(BaseModel):
    is_captured: Optional[bool] = None
    capture_date: Optional[datetime] = None
    nickname: Optional[str] = None
    favorite: Optional[bool] = None

class PokedexEntryOut(BaseModel):
    id: int
    pokemon_id: int
    pokemon_name: Optional[str]
    nickname: Optional[str]
    is_captured: bool
    favorite: bool
    capture_date: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }