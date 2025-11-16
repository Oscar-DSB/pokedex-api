import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, delete
from app.main import app
from app.database import engine
from app.models import User, PokedexEntry
from app.auth import get_password_hash

os.environ["TESTING"] = "true"  # Desactivar rate limiter


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def create_test_user():
    """
    Crea los usuarios necesarios para los tests:
    - ash / pikachu        (para la mayoría)
    - Ash / Pikachu123     (para test_login_success)
    """
    with Session(engine) as session:

        # Usuario ash (minúsculas)
        user = session.exec(select(User).where(User.username == "ash")).first()
        if not user:
            hashed_pw = get_password_hash("pikachu")
            user = User(
                username="ash",
                email="ash@example.com",
                hashed_password=hashed_pw
            )
            session.add(user)

        # Usuario Ash (mayúscula inicial)
        user2 = session.exec(select(User).where(User.username == "Ash")).first()
        if not user2:
            hashed_pw2 = get_password_hash("Pikachu123")
            user2 = User(
                username="Ash",
                email="Ash@example.com",
                hashed_password=hashed_pw2
            )
            session.add(user2)

        session.commit()

        # Devolver solo el usuario principal (ash)
        return {"username": "ash", "password": "pikachu"}


@pytest.fixture(scope="session")
def test_user(create_test_user):
    return create_test_user


@pytest.fixture(autouse=True)
def clean_pokedex():
    """Eliminar entradas de Pokédex entre tests para evitar duplicados."""
    with Session(engine) as session:
        session.exec(delete(PokedexEntry))
        session.commit()
    yield


@pytest.fixture(scope="module")
def auth_headers(client, test_user):
    r = client.post("/api/v1/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
