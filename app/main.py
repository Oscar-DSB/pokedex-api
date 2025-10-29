# archivo: app/main.py
from fastapi import FastAPI
from app.routers import pokemon  # Importamos el router del módulo Pokémon
import logging

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,  # Nivel de logs que se mostrarán (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Crear instancia de la aplicación FastAPI
app = FastAPI(title="Pokedex API")

# Ruta raíz (comprobación básica)
@app.get("/")
def read_root():
    return {"message": "Bienvenido a la Pokédex API 🧩"}

# Incluir el router de Pokémon
app.include_router(pokemon.router)
