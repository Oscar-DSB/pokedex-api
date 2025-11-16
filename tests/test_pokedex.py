# tests/test_pokedex.py
import pytest
from fastapi.testclient import TestClient

# -----------------------------
# 🔹 Fixtures de autenticación
# -----------------------------
@pytest.fixture
def auth_headers(client, test_user):
    # Primero hacemos login y obtenemos token
    r = client.post("/api/v1/auth/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# -----------------------------
# 🔹 Tests de Pokédex
# -----------------------------
def test_add_pokemon_to_pokedex(client: TestClient, auth_headers):
    """Añadir Pokémon a la Pokédex"""
    data = {"pokemon_id": 25, "nickname": "Pika", "is_captured": True}
    r = client.post("/api/v1/pokedex", headers=auth_headers, json=data)
    assert r.status_code == 200
    assert r.json()["pokemon_name"].lower() == "pikachu"

def test_add_duplicate_pokemon(client: TestClient, auth_headers):
    """No permitir duplicados"""
    data = {"pokemon_id": 1, "nickname": "Bulby", "is_captured": True}
    client.post("/api/v1/pokedex", headers=auth_headers, json=data)
    r = client.post("/api/v1/pokedex", headers=auth_headers, json=data)
    assert r.status_code == 400
    assert "Ya tienes este Pokémon" in r.text

def test_get_pokedex_with_filters(client: TestClient, auth_headers):
    """Filtrar por capturados o favoritos"""
    # Añadimos dos Pokémon
    client.post("/api/v1/pokedex", headers=auth_headers, json={"pokemon_id": 4, "is_captured": True})
    client.post("/api/v1/pokedex", headers=auth_headers, json={"pokemon_id": 7, "is_captured": False})
    r = client.get("/api/v1/pokedex?captured=true", headers=auth_headers)
    assert r.status_code == 200
    results = r.json()
    assert all(p["is_captured"] for p in results)

def test_update_pokedex_entry(client: TestClient, auth_headers):
    """Actualizar entrada existente"""
    data = {"pokemon_id": 133, "nickname": "Eevee", "is_captured": True}
    created = client.post("/api/v1/pokedex", headers=auth_headers, json=data).json()
    entry_id = created["id"]
    r = client.patch(f"/api/v1/pokedex/{entry_id}", headers=auth_headers, json={"favorite": True})
    assert r.status_code == 200
    assert r.json()["favorite"] is True

def test_delete_pokedex_entry(client: TestClient, auth_headers):
    """Eliminar entrada de la Pokédex"""
    data = {"pokemon_id": 10, "nickname": "Caterpie", "is_captured": True}
    entry = client.post("/api/v1/pokedex", headers=auth_headers, json=data).json()
    entry_id = entry["id"]
    r = client.delete(f"/api/v1/pokedex/{entry_id}", headers=auth_headers)
    assert r.status_code == 200
    assert "eliminada" in r.text.lower()

def test_export_pokedex_csv(client, auth_headers):
    """Exporta Pokédex en CSV"""
    client.post("/api/v1/pokedex", headers=auth_headers, json={"pokemon_id": 1, "is_captured": True})
    r = client.get("/api/v1/pokedex/export?format=csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "Nombre" in r.text


def test_export_pokedex_pdf(client, auth_headers):
    """Exporta Pokédex en PDF"""
    client.post("/api/v1/pokedex", headers=auth_headers, json={"pokemon_id": 4, "is_captured": True})
    r = client.get("/api/v1/pokedex/export?format=pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_pokedex_stats(client, auth_headers):
    """Devuelve estadísticas correctas"""
    client.post("/api/v1/pokedex", headers=auth_headers, json={"pokemon_id": 7, "is_captured": True})
    r = client.get("/api/v1/pokedex/stats", headers=auth_headers)
    assert r.status_code == 200
    stats = r.json()
    assert "total_pokemon" in stats
    assert "captured" in stats