# archivo: app/database.py
from sqlmodel import SQLModel, create_engine, Session
import os

# Usamos SQLite por defecto (puedes cambiar a PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pokedex.db")

# echo=True muestra todas las queries en consola (útil para debug)
engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """Crea las tablas si no existen."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Genera una sesión de base de datos."""
    with Session(engine) as session:
        yield session
