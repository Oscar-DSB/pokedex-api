from fastapi import APIRouter, Query, Path, HTTPException, Depends
from app.services.pokeapi_service import PokeAPIService
from app.auth import get_current_user
from app.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/pokemon",
    tags=["pokemon"],
    #  Protegemos el router con JWT
    dependencies=[Depends(get_current_user)]
)
service = PokeAPIService()

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}

@router.get("/{id_or_name}")
def get_pokemon(id_or_name: str, ):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/{id_or_name}")
    try:
        data = service.get_pokemon(id_or_name)
        logger.info(f"Pokémon encontrado: {data['name']} (ID {data['id']})")
        return {
            "id": data["id"],
            "name": data["name"].capitalize(),
            "sprite": data["sprites"]["front_default"],
            "types": [t["type"]["name"] for t in data["types"]],
        }
    except HTTPException as e:
        logger.error(f"Error al obtener '{id_or_name}': {e.detail}")
        raise

@router.get("")
@router.get("/", include_in_schema=False)
def search_pokemons(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon?limit={limit}&offset={offset}")
    try:
        data = service.search_pokemons(limit=limit, offset=offset)
        results = []
        for item in data.get("results", []):
            url = item["url"].rstrip("/")
            poke_id = int(url.split("/")[-1])
            results.append({
                "id": poke_id,
                "name": item["name"].capitalize(),
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
            })
        logger.info(f"Listado generado: {len(results)} elementos")
        return {"count": data.get("count", len(results)), "results": results}
    except HTTPException as e:
        logger.error(f"Error al listar pokémon: {e.detail}")
        raise

@router.get("/type/{type_name}")
def get_pokemon_by_type(
    type_name: str = Path(..., description="Tipo de Pokémon (fire, water, grass, etc.)")
):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/type/{type_name}")
    try:
        data = service.get_pokemon_by_type(type_name)
        results = []
        for item in data.get("pokemon", []):
            pokemon = item["pokemon"]
            url = pokemon["url"].rstrip("/")
            poke_id = int(url.split("/")[-1])
            results.append({
                "id": poke_id,
                "name": pokemon["name"].capitalize(),
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
            })
        logger.info(f"Tipo '{data['name']}' → {len(results)} elementos")
        return {"type": data["name"].capitalize(), "count": len(results), "results": results}
    except HTTPException as e:
        logger.error(f"Error al listar por tipo '{type_name}': {e.detail}")
        raise

@router.get("/species/{id_or_name}")
def get_pokemon_species(id_or_name: str):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/species/{id_or_name}")
    try:
        data = service.get_inf_especies(id_or_name)
        species_info = {
            "id": data.get("id"),
            "name": data.get("name", "").capitalize(),
            "color": (data.get("color") or {}).get("name"),
            "habitat": (data.get("habitat") or {}).get("name"),
            "shape": (data.get("shape") or {}).get("name"),
            "is_legendary": data.get("is_legendary", False),
            "is_mythical": data.get("is_mythical", False),
        }
        # Descripción: prioriza ES y cae a EN si no hay
        desc = None
        for entry in data.get("flavor_text_entries", []):
            if entry["language"]["name"] == "es":
                desc = entry["flavor_text"]; break
        if desc is None:
            for entry in data.get("flavor_text_entries", []):
                if entry["language"]["name"] == "en":
                    desc = entry["flavor_text"]; break
        if desc:
            species_info["description"] = desc.replace("\n", " ").replace("\f", " ")
        logger.info(f"Especie '{species_info['name']}' obtenida (ID {species_info['id']})")
        return species_info
    except HTTPException as e:
        logger.error(f"Error al obtener especie '{id_or_name}': {e.detail}")
        raise
