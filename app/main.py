# archivo: app/main.py
from fastapi import FastAPI
from app.routers import pokemon  # Importamos el router del módulo Pokémon

# Crear instancia de la aplicación FastAPI
app = FastAPI(title="Pokedex API")

# Ruta raíz (comprobación básica)
@app.get("/")
def read_root():
    return {"message": "Bienvenido a la Pokédex API 🧩"}

# Incluir el router de Pokémon
app.include_router(pokemon.router)
