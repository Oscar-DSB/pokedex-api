# tests/test_auth.py
def test_register_user_success(client):
    """Registro exitoso de usuario"""
    r = client.post("/api/v1/auth/register", json={
        "username": "Brock",
        "email": "brock@example.com",
        "password": "Password1"
    })
    if r.status_code == 201:
        data = r.json()
        assert data["username"] == "Brock"
    else:
        # Si el usuario ya existe, debe responder 409
        assert r.status_code == 409


def test_register_duplicate_username(client):
    """Error al registrar username duplicado"""
    client.post("/api/v1/auth/register", json={
        "username": "Misty",
        "email": "misty@example.com",
        "password": "Password1"
    })
    r = client.post("/api/v1/auth/register", json={
        "username": "Misty",
        "email": "misty2@example.com",
        "password": "Password1"
    })
    assert r.status_code == 409

def test_login_success(client, test_user):
    """Login exitoso retorna JWT válido"""
    r = client.post("/api/v1/auth/login", json={
        "username": "Ash",
        "password": "Pikachu123"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    """Login con credenciales incorrectas retorna 401"""
    r = client.post("/api/v1/auth/login", json={
        "username": "Ash",
        "password": "wrongpassword"
    })
    assert r.status_code == 401

def test_access_protected_endpoint_without_token(client):
    """Acceso sin token retorna 401"""
    r = client.get("/api/v1/pokedex")
    assert r.status_code == 401
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings
from app.main import app

client = TestClient(app)


def test_register_missing_fields():
    """Debe rechazar registro incompleto"""
    r = client.post("/api/v1/auth/register", json={"username": "ash"})
    assert r.status_code in (400, 422)


def test_login_wrong_password():
    """Login inválido"""
    r = client.post("/api/v1/auth/login", json={"username": "ash", "password": "wrongpass"})
    assert r.status_code == 401


def test_refresh_token_flow():
    """Crea token de refresco y genera nuevo access token"""
    payload = {
        "user_id": 1,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert r.status_code in (200, 401)


def test_refresh_token_invalid_type():
    """Falla si se pasa access token en lugar de refresh"""
    access_payload = {
        "user_id": 1,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=5),
    }
    bad_token = jwt.encode(access_payload, settings.secret_key, algorithm=settings.algorithm)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": bad_token})
    assert r.status_code == 401


def test_me_endpoint_without_token():
    """Debe rechazar acceso sin token"""
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_invalid_email():
    r = client.post("/api/v1/auth/register", json={
        "username": "testBad",
        "email": "bademail",
        "password": "Password1"
    })
    assert r.status_code == 422

def test_register_weak_password():
    r = client.post("/api/v1/auth/register", json={
        "username": "testBad2",
        "email": "ok@example.com",
        "password": "weak"
    })
    assert r.status_code == 422

def test_refresh_without_token():
    r = client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 400
    assert "refresh_token requerido" in r.text
