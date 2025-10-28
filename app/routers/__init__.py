from fastapi import APIRouter
from . import pokemon

v1 = APIRouter(prefix="/api/v1")
v1.include_router(pokemon.router)
