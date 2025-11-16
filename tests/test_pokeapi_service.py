import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

#   Asegurar modo testing y limiter desactivado
os.environ["TESTING"] = "true"

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """Devuelve encabezado JWT válido (usuario ya creado desde conftest)."""
    r = client.post("/api/v1/auth/login", json={
        "username": "ash",
        "password": "pikachu"
    })
    assert r.status_code == 200, f"Login fallido: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
#                              TESTS PRINCIPALES
# ---------------------------------------------------------------------------

def test_get_pokemon_detail_success(auth_headers):
    """Debe devolver detalles del Pokémon por ID o nombre."""
    for name in ["pikachu", "bulbasaur"]:
        r = client.get(f"/api/v1/pokemon/{name}", headers=auth_headers)
        assert r.status_code == 200, f"Error con {name}: {r.text}"
        data = r.json()
        assert "id" in data and "name" in data
        assert data["name"].lower() == name


def test_get_pokemon_species(auth_headers):
    """Debe devolver información de especie del Pokémon."""
    r = client.get("/api/v1/pokemon/species/25", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert isinstance(data["id"], int)


def test_get_pokemon_card_png(auth_headers):
    """Debe devolver la tarjeta PNG de un Pokémon."""
    r = client.get("/api/v1/pokemon/25/card?format=png", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")


def test_get_pokemon_card_pdf(auth_headers):
    """Debe devolver la tarjeta PDF de un Pokémon."""
    r = client.get("/api/v1/pokemon/25/card?format=pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_search_pokemon_by_name(auth_headers):
    """Debe permitir buscar Pokémon por nombre parcial."""
    r = client.get("/api/v1/pokemon/search?name=pika", headers=auth_headers)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body, (dict, list))


def test_get_pokemon_type_list(monkeypatch, auth_headers):
    """Mock de la PokeAPI: lista por tipo."""
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "name": "electric",
                "pokemon": [
                    {"pokemon": {"name": "pikachu", "url": "https://pokeapi.co/api/v2/pokemon/25/"}},
                    {"pokemon": {"name": "raichu", "url": "https://pokeapi.co/api/v2/pokemon/26/"}},
                ]
            }

    import app.services.pokeapi_service as svc
    monkeypatch.setattr(svc.httpx, "get", lambda *a, **kw: MockResponse())

    r = client.get("/api/v1/pokemon/type/electric", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["type"].lower() == "electric"
    assert any(p["name"].lower() == "pikachu" for p in data["results"])


def test_search_pokemons_limit_offset(auth_headers):
    """Debe aceptar paginación correctamente."""
    r = client.get("/api/v1/pokemon?limit=5&offset=0", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    if data["results"]:
        assert "name" in data["results"][0]


def test_get_pokemon_not_found(monkeypatch, auth_headers):
    """Simula error 404 de la PokeAPI."""
    class MockResponse:
        status_code = 404
        def json(self):
            return {"detail": "Not found"}

    import app.services.pokeapi_service as svc
    monkeypatch.setattr(svc.httpx, "get", lambda *a, **kw: MockResponse())

    r = client.get("/api/v1/pokemon/fakepokemon", headers=auth_headers)
    assert r.status_code in (404, 400, 500)

