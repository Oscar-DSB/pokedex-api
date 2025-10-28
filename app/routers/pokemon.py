from fastapi import APIRouter
from app.services.pokeapi_service import PokeAPIService

router = APIRouter(prefix="/api/v1/pokemon", tags=["pokemon"])
service = PokeAPIService()

@router.get("/{id_or_name}")
def get_pokemon(id_or_name: str):
    """Devuelve información básica de un Pokémon."""
    data = service.get_pokemon(id_or_name)
    return {
        "id": data["id"],
        "name": data["name"].capitalize(),
        "sprite": data["sprites"]["front_default"],
        "types": [t["type"]["name"] for t in data["types"]],
    }
@router.get("/search")
def search_pokemons(limit: int , offset: int ):
    data = service.search_pokemons(limit = limit, offset=offset)
    results = []
    for item in data.get("results",[]):
        url = item["url"].rstrip("/")
        poke_id = int(url.split("/")[-1])
        results.append({
            "id": poke_id,
            "name": item["name"].capitalize(),
            "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
        })
    return {"count": data.get("count", len(results)), "results": results}

