from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.rate_limiter import limiter
from app.database import init_db
from app.routers import auth as auth_router
from app.routers import pokemon
from app.routers import pokedex
import logging

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,  # Nivel de logs que se mostrarán (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Pokedex API")

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta raíz (comprobación básica)
@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(pokemon.router)
app.include_router(auth_router.router)
app.include_router(pokedex.router)