from typing import Any, Dict
import httpx
import time
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"
    TTL = 300  # 5 minutos de caché

    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}

    # ---------- Caché ----------
    def _cache_get(self, key: str):
        item = self.cache.get(key)
        if item and (time.time() - item["ts"] < self.TTL):
            return item["value"]
        return None

    def _cache_set(self, key: str, value: Any):
        self.cache[key] = {"value": value, "ts": time.time()}

    # ---------- Llamadas HTTP ----------
    def _get(self, path: str, params: Dict | None = None) -> Any:
        key = f"{path}|{params or {}}"
        if (cached := self._cache_get(key)) is not None:
            logger.info(f"[CACHE HIT] {path}")
            return cached

        url = f"{self.BASE_URL}/{path.lstrip('/')}"
        logger.info(f"[CACHE MISS] {url}")

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                self._cache_set(key, data)
                return data
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

        except httpx.TimeoutException as e:
            logger.error(f"Timeout con PokeAPI: {e}")
            raise HTTPException(status_code=504, detail="Timeout con PokeAPI")

        except httpx.RequestError as e:
            logger.error(f"Error de conexión con PokeAPI: {e}")
            raise HTTPException(status_code=503, detail="Error al conectar con PokeAPI")


    # ---------- Métodos públicos ----------
    def get_pokemon(self, id_or_name: str | int) -> Dict[str, Any]:
        return self._get(f"pokemon/{id_or_name}")

    def get_species(self, id_or_name: str | int) -> Dict[str, Any]:
        return self._get(f"pokemon-species/{id_or_name}")

    def search_pokemon_by_name(self, name: str, limit: int = 20, offset: int = 0):

        name = name.lower().strip()
        if not name:
            return []

        # obtenemos la lista completa de nombres
        listing = self._get("pokemon", params={"limit": 2000})
        all_names = [item["name"] for item in listing.get("results", [])]
        matches = [nm for nm in all_names if name in nm]

        results = []
        for nm in matches[offset:offset + limit]:
            try:
                data = self.get_pokemon(nm)
                results.append({
                    "id": data["id"],
                    "name": data["name"],
                    "sprite": data["sprites"]["front_default"],
                    "types": [t["type"]["name"] for t in data["types"]],
                })
            except HTTPException:
                continue
        return results

    def search_pokemons(self, limit: int = 20, offset: int = 0):
        return self._get("pokemon", params={"limit": limit, "offset": offset})

    def get_pokemon_by_type(self, type_name: str):
        return self._get(f"type/{type_name}")
