import requests
import time
from typing import Optional, Dict, Tuple
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class PokeAPIService:
    BASE_URL = "https://pokeapi.co/api/v2"

    def __init__(self):
        # Caché en memoria simple: {(path, params): (expires_at, data)}
        self.cache: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Tuple[float, Dict]] = {}
        self.ttl = 300

    def _make_cache_key(self, path: str, params: Optional[Dict]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        """Crea una clave estable basada en path y parámetros."""
        return (path, tuple(sorted((params or {}).items())))

    def _get_from_cache(self, key: Tuple[str, Tuple[Tuple[str, str], ...]]) -> Optional[Dict]:
        """Devuelve un valor si no ha expirado."""
        cached = self.cache.get(key)
        if not cached:
            return None
        expires_at, data = cached
        if expires_at < time.time():
            logger.info(f"[CACHE EXPIRED] {key[0]} params={key[1]}")
            self.cache.pop(key, None)
            return None
        return data

    def _store_in_cache(self, key: Tuple[str, Tuple[Tuple[str, str], ...]], data: Dict):
        """Guarda el valor con timestamp de expiración."""
        expires_at = time.time() + self.ttl
        self.cache[key] = (expires_at, data)
        logger.info(f"[CACHE STORE] {key[0]} guardado hasta {time.strftime('%H:%M:%S', time.localtime(expires_at))}")

    def _get(self, path: str, params: Optional[Dict] = None, timeout: int = 10) -> Dict:
        url = f"{self.BASE_URL}{path}"
        key = self._make_cache_key(path, params)

        # 1️⃣ Intentar caché
        cached = self._get_from_cache(key)
        if cached is not None:
            logger.info(f"[CACHE HIT] {url} params={params}")
            return cached
        logger.info(f"[CACHE MISS] {url} params={params}")

        # 2️⃣ Si no está en caché, llamar a la API
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            logger.info(f"Respuesta de PokeAPI {resp.status_code} para {resp.url}")

            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Recurso no encontrado en PokeAPI")
            if 500 <= resp.status_code <= 599:
                raise HTTPException(status_code=502, detail="Error de PokeAPI (upstream)")
            if 400 <= resp.status_code <= 499:
                resp.raise_for_status()

            data = resp.json()
            # 3️⃣ Guardar en caché solo si OK
            self._store_in_cache(key, data)
            return data

        except requests.exceptions.Timeout:
            logger.error(f"Timeout al consultar {url}")
            raise HTTPException(status_code=408, detail="Timeout Error")

        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión con {url}")
            raise HTTPException(status_code=503, detail="Error connecting to PokeAPI")

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if getattr(e, "response", None) else 502
            detail = e.response.text if getattr(e, "response", None) else str(e)
            raise HTTPException(status_code=status, detail=detail)

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error inesperado al consultar {url}: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error")

    def get_pokemon(self, identifier: str | int) -> Dict:
        return self._get(f"/pokemon/{str(identifier).lower()}")

    def search_pokemons(self, limit: int = 20, offset: int = 0) -> Dict:
        return self._get("/pokemon", params={"limit": limit, "offset": offset})

    def get_pokemon_by_type(self, type_name: str) -> Dict:
        return self._get(f"/type/{str(type_name).lower()}")

    def get_inf_especies(self, id_or_name: str | int) -> Dict:
        return self._get(f"/pokemon-species/{str(id_or_name).lower()}")
