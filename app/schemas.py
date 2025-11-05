from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


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

class PokedexEntryBase(BaseModel):
    """Campos comunes para entradas de Pokédex"""
    pokemon_id: int
    pokemon_name: str
    pokemon_sprite: str
    nickname: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)
    favorite: bool = False
    is_captured: bool = False


class PokedexEntryCreate(PokedexEntryBase):
    """Datos necesarios para crear una entrada"""
    pass


class PokedexEntryRead(PokedexEntryBase):
    """Datos que devuelve la API al consultar una entrada"""
    id: int
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TeamBase(BaseModel):
    name: str = Field(max_length=100)
    description: Optional[str] = None

class TeamCreate(TeamBase):
    pass

class TeamRead(TeamBase):
    id: int
    trainer_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TeamMemberBase(BaseModel):
    team_id: int
    pokedex_entry_id: int
    position: int = Field(ge=1, le=6)

class TeamMemberCreate(TeamMemberBase):
    pass

class TeamMemberRead(TeamMemberBase):
    id: int
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