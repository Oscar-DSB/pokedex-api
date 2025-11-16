from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, CheckConstraint, Index


# =========================
# USER
# =========================
class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    email: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    # Relaciones
    pokedex_entries: List["PokedexEntry"] = Relationship(back_populates="owner")
    teams: List["Team"] = Relationship(back_populates="trainer")


# =========================
# POKEDEX ENTRY
# =========================
class PokedexEntry(SQLModel, table=True):
    __tablename__ = "pokedexentry"
    __table_args__ = (
        UniqueConstraint("user_id", "pokemon_id", name="uq_pokedex_user_pokemon"),
        Index("ix_pokedex_user", "user_id"),
        Index("ix_pokedex_pokemon", "pokemon_id"),
        {"sqlite_autoincrement": True},
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    pokemon_id: int
    pokemon_name: Optional[str] = None
    nickname: Optional[str] = None
    is_captured: bool = False
    favorite: bool = False
    capture_date: Optional[datetime] = None

    owner: Optional[User] = Relationship(back_populates="pokedex_entries")
    team_members: List["TeamMember"] = Relationship(back_populates="pokedex_entry")


# =========================
# TEAM
# =========================
class Team(SQLModel, table=True):
    __tablename__ = "team"
    __table_args__ = (
        Index("ix_team_trainer", "trainer_id"),
        {"sqlite_autoincrement": True},
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    trainer_id: int = Field(foreign_key="user.id", index=True)
    name: str
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    trainer: Optional[User] = Relationship(back_populates="teams")
    members: List["TeamMember"] = Relationship(back_populates="team")


# =========================
# TEAM MEMBER
# =========================
class TeamMember(SQLModel, table=True):
    __tablename__ = "teammember"
    __table_args__ = (
        UniqueConstraint("team_id", "position", name="uq_teammember_team_position"),
        UniqueConstraint("team_id", "pokedex_entry_id", name="uq_teammember_team_entry"),
        CheckConstraint("position BETWEEN 1 AND 6", name="ck_teammember_pos"),
        Index("ix_teammember_team", "team_id"),
        {"sqlite_autoincrement": True},
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    pokedex_entry_id: int = Field(foreign_key="pokedexentry.id", index=True)
    position: int

    team: Optional[Team] = Relationship(back_populates="members")
    pokedex_entry: Optional[PokedexEntry] = Relationship(back_populates="team_members")
