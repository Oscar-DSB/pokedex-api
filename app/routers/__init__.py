from fastapi import APIRouter
from . import auth, pokemon, pokedex, teams

# ============================
# VERSIÓN 1 (estable)
# ============================
v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router)
v1_router.include_router(pokemon.router)
v1_router.include_router(pokedex.router)
v1_router.include_router(teams.router)

# ============================
# VERSIÓN 2 (experimental)
# ============================
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/pokedex", summary="Pokédex v2 con evoluciones automáticas")
def get_pokedex_v2():
    return {"message": "Versión 2 - incluye evoluciones automáticas"}

routers = [v1_router, v2_router]