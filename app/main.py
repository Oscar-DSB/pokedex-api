from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from slowapi.errors import RateLimitExceeded
import logging, os, sys
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import v1_router

# Codificación correcta en Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pokedex_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("pokedex_api")

# =========================
# RATE LIMITER
# =========================
from app.rate_limiter import limiter

# =========================
# LIFESPAN (startup/shutdown)
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando base de datos...")
    init_db()
    logger.info("Base de datos lista.")
    yield
    logger.info("Cierre de aplicación.")

# =========================
# APP PRINCIPAL
# =========================
app = FastAPI(
    title="Pokédex API",
    version="2.0",
    description="API REST de Pokédex con autenticación, Pokédex personal y equipos de batalla.",
    lifespan=lifespan,
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host} on {request.url.path}")
    return JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes, inténtalo más tarde."})

app.state.limiter = limiter

# Middleware de logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{response.status_code} {request.url.path}")
    return response

# =========================
# VERSIONADO
# =========================
app.include_router(v1_router)

# =========================
# OPENAPI con Bearer JWT
# =========================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
