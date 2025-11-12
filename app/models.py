# app/models.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="user")
    teams: List["Team"] = Relationship(back_populates="trainer")



class PokedexEntry(SQLModel, table=True):
    __tablename__ = "pokedexentry"
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    pokemon_id: int = Field(index=True)
    pokemon_name: Optional[str] = None
    nickname: Optional[str] = None
    is_captured: bool = Field(default=False)
    favorite: bool = Field(default=False)
    capture_date: Optional[datetime] = None
    user: Optional["User"] = Relationship(back_populates="pokedex_entries")

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trainer_id: int = Field(foreign_key="user.id", index=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    trainer: Optional["User"] = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")


class TeamMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    pokedex_entry_id: int = Field(foreign_key="pokedexentry.id", index=True)
    position: int = Field(ge=1, le=6)

    team: Optional["Team"] = Relationship(back_populates="members")
