import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------
# 🔹 Crear equipo
# ---------------------------------------------------
def test_create_team(client: TestClient, auth_headers):
    """Crear un equipo nuevo"""
    r = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "Team Rocket",
        "description": "Atrapar pokémon ajenos",
        "pokemon_ids": []
    })
    assert r.status_code in (201, 200), r.text
    data = r.json()
    assert "id" in data
    assert data["name"] == "Team Rocket"

# ---------------------------------------------------
# 🔹 Listar equipos
# ---------------------------------------------------
def test_get_teams_list(client: TestClient, auth_headers):
    """Listar equipos del usuario"""
    r = client.get("/api/v1/teams", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)

# ---------------------------------------------------
# 🔹 Añadir miembro a un equipo
# ---------------------------------------------------
def test_add_member_to_team(client: TestClient, auth_headers):
    """Añadir un Pokémon al equipo"""
    # Crear equipo vacío
    team = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "Elite Four",
        "description": "Campeones regionales",
        "pokemon_ids": []
    }).json()
    assert "id" in team, team

    # Crear pokédex entry
    pokedex_entry = client.post("/api/v1/pokedex", headers=auth_headers, json={
        "pokemon_id": 6,  # Charizard
        "is_captured": True
    }).json()
    assert "id" in pokedex_entry, pokedex_entry

    # Actualizar equipo con Pokémon
    r = client.put(f"/api/v1/teams/{team['id']}", headers=auth_headers, json={
        "pokemon_ids": [6]
    })
    assert r.status_code in (200, 201), r.text
    updated = r.json()
    assert updated["id"] == team["id"]

# ---------------------------------------------------
# 🔹 Actualizar equipo existente
# ---------------------------------------------------
def test_update_team(client: TestClient, auth_headers):
    """Actualizar equipo existente"""
    team = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "Valor",
        "description": "Original team"
    }).json()
    assert "id" in team, team

    r = client.put(f"/api/v1/teams/{team['id']}", headers=auth_headers, json={
        "description": "Updated description"
    })
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["description"] == "Updated description"

# ---------------------------------------------------
# 🔹 Eliminar equipo
# ---------------------------------------------------
def test_delete_team(client: TestClient, auth_headers):
    """Eliminar equipo"""
    team = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "DeleteMe",
        "description": "To be removed"
    }).json()
    assert "id" in team, team

    r = client.delete(f"/api/v1/teams/{team['id']}", headers=auth_headers)
    assert r.status_code in (200, 204), r.text

# ---------------------------------------------------
# 🔹 Exportar equipo como PDF
# ---------------------------------------------------
def test_export_team_pdf(client: TestClient, auth_headers):
    """Exportar equipo como PDF"""
    team = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "PDF Squad",
        "description": "Testing export"
    }).json()
    assert "id" in team, team

    # Añadir Pokémon capturado
    client.post("/api/v1/pokedex", headers=auth_headers, json={
        "pokemon_id": 25,  # Pikachu
        "is_captured": True
    })

    client.put(f"/api/v1/teams/{team['id']}", headers=auth_headers, json={
        "pokemon_ids": [25]
    })

    # Exportar PDF
    r = client.get(f"/api/v1/teams/{team['id']}/export", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert b"%PDF" in r.content[:10]  # verificación simple de encabezado PDF

def test_update_team_invalid_pokemon(client, auth_headers):
    team = client.post("/api/v1/teams", headers=auth_headers, json={
        "name": "InvalidTeam"
    }).json()

    r = client.put(f"/api/v1/teams/{team['id']}", headers=auth_headers, json={
        "pokemon_ids": [99999]  # nunca estará en pokédex
    })
    assert r.status_code == 400
