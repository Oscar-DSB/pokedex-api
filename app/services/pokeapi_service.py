import requests
from typing import Optional, List, Dict
from fastapi import HTTPException
import logging
logger = logging.getLogger(__name__)
class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def _get(self, path: str, params: Optional[Dict] = None, timeout: int = 0.001) -> Dict:
        url = f"{self.BASE_URL}{path}"
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            logger.info("PokeAPI GET %s -> %s", resp.url, resp.status_code)
        except requests.exceptions.HTTPError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except requests.exceptions.ConnectionError as e:
            raise HTTPException(status_code=503, detail="Error connecting to PokeAPI")
        except requests.exceptions.Timeout as e:
            logger.error("PokeAPI GET timed out")
            raise HTTPException(status_code=408, detail="Timeout Error")
        return resp.json()

    def get_pokemon(self, identifier: str | int) -> Dict:
        return self._get(f"/pokemon/{str(identifier).lower()}")
    def search_pokemons(self,limit: int = 20,offset: int = 0) -> Dict:
        return self._get("/pokemon", params={"limit": limit, "offset": offset})


def get_pokemon_by_type(self, type_name: str) -> List[Dict]:
     """Obtiene todos los Pokémon de un tipo específico"""
     pass
