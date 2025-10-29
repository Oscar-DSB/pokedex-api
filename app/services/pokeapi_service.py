import requests
from typing import Optional, List, Dict
from fastapi import HTTPException
import logging
logger = logging.getLogger(__name__)
class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def _get(self, path: str, params: Optional[Dict] = None, timeout: int = 10) -> Dict:
        url = f"{self.BASE_URL}{path}"
        logger.info(f"Llamando a PokeAPI: {url} con params={params}")

        try:
            resp = requests.get(url, params=params, timeout=timeout)
            logger.info(f"Respuesta de PokeAPI {resp.status_code} para {resp.url}")

            # --- Mapeo explícito y determinista ---
            if resp.status_code == 404:
                # mensaje claro para tu API (no el HTML de PokeAPI)
                raise HTTPException(status_code=404, detail="Recurso no encontrado en PokeAPI")
            if 500 <= resp.status_code <= 599:
                raise HTTPException(status_code=502, detail="Error de PokeAPI (upstream)")
            if 400 <= resp.status_code <= 499:
                # otros 4xx: deja que requests construya el motivo (400, 401, 403…)
                resp.raise_for_status()

            return resp.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout al consultar {url}")
            raise HTTPException(status_code=408, detail="Timeout Error")

        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión con {url}")
            raise HTTPException(status_code=503, detail="Error connecting to PokeAPI")

        except requests.exceptions.HTTPError as e:
            # fallback por si raise_for_status() lanza sin response
            status = e.response.status_code if getattr(e, "response", None) else 502
            detail = e.response.text if getattr(e, "response", None) else str(e)
            raise HTTPException(status_code=status, detail=detail)

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error inesperado al consultar {url}: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error")

    def get_pokemon(self, identifier: str | int) -> Dict:
        return self._get(f"/pokemon/{str(identifier).lower()}")

    def search_pokemons(self,limit: int = 20,offset: int = 0) -> Dict:
        return self._get("/pokemon", params={"limit": limit, "offset": offset})

    def get_pokemon_by_type(self, type_name: str) -> Dict:
        return self._get(f"/type/{str(type_name).lower()}")

    def get_inf_especies(self, id_or_name: str |int) -> Dict:
        return self._get(f"/pokemon-species/{str(id_or_name).lower()}")
