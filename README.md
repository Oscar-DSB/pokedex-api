# 🐾 Pokédex API — FastAPI + SQLModel + PokeAPI

API REST completa para gestionar una **Pokédex personal**, equipos de batalla y consultar información real de Pokémon utilizando la **PokeAPI**.  
Proyecto desarrollado como parte de la *Práctica 1 — API REST* del Módulo 2.

---

## 🚀 Características Principales

### 🔐 Autenticación JWT
- Registro y login con validación de email y contraseña.
- Tokens **access** y **refresh** (renovación sin re-login).
- Hash seguro de contraseñas con `bcrypt`.

### 📚 Pokédex Personal
- Añadir Pokémon capturados.
- Evitar duplicados.
- Marcar favoritos, añadir apodos, notas…
- Filtrado, ordenación y paginación.
- Exportación en **CSV** y **PDF**.
- Estadísticas completas:
  - Pokémon totales
  - Capturados
  - Favoritos
  - Tipo más común
  - Racha de capturas
  - Porcentaje completado

### ⚔️ Equipos de Batalla
- Crear equipos de hasta 6 Pokémon.
- Añadir solo Pokémon capturados.
- Exportar equipo en PDF con fichas.

### 🧩 Integración con la PokeAPI
- Consultar Pokémon por ID o nombre.
- Consultar especies.
- Buscar por tipo.
- Generar tarjetas estilo TCG en **PNG** o **PDF**.

### 🛡 Seguridad
- Rate limiting por endpoint.
- Logging estructurado completo.
- CORS configurado.
- Validación estricta de inputs.

### 🧪 Testing
- Suite completa con **pytest**.
- Más de 30 tests:
  - autenticación  
  - pokédex  
  - equipos  
  - PokeAPI  
  - exports  
  - rate limiting  
- Cobertura: **88%** (supera el 80% requerido)

---

## 📂 Estructura del Proyecto

```
pokedex-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── auth.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── pokedex.py
│   │   ├── pokemon.py
│   │   └── teams.py
│   └── services/
│       └── pokeapi_service.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_pokedex.py
│   ├── test_pokeapi_service.py
│   ├── test_team.py
│   └── test_rate_limiter_disabled.py
├── requirements.txt
├── pyproject.toml
├── SECURITY.md
├── .env.example
└── README.md
```

---

## ⚙️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tuusuario/pokedex-api.git
cd pokedex-api
```

### 2. Crear entorno virtual
```bash
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## 🔧 Configuración

Crea un archivo **.env** con esta plantilla:

```
SECRET_KEY=change_me_to_a_secure_random_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=sqlite:///./pokedex.db
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
TESTING=false
```

Un archivo `.env.example` ya está incluido en el repo.

---

## ▶️ Ejecución de la API

Iniciar el servidor:

```bash
uvicorn app.main:app --reload
```

Documentación interactiva:

📄 Swagger UI → http://localhost:8000/docs  
📄 ReDoc → http://localhost:8000/redoc  

---

## 🔗 Endpoints Principales

### 🔐 **Autenticación**
| Método | URL | Descripción |
|--------|-----|-------------|
| POST | /api/v1/auth/register | Registrar usuario |
| POST | /api/v1/auth/login | Login y token JWT |
| POST | /api/v1/auth/refresh | Nuevo access token |
| GET | /api/v1/auth/me | Usuario autenticado |

---

### 📚 **Pokédex**
| Método | URL | Descripción |
|--------|-----|-------------|
| POST | /api/v1/pokedex | Añadir Pokémon |
| GET | /api/v1/pokedex | Listar con filtros |
| PATCH | /api/v1/pokedex/{id} | Actualizar entrada |
| DELETE | /api/v1/pokedex/{id} | Eliminar |
| GET | /api/v1/pokedex/export | Export CSV/PDF |
| GET | /api/v1/pokedex/stats | Estadísticas |

---

### 🧩 **Pokémon (PokeAPI Proxy)**
| Método | URL | Descripción |
|--------|------|------------|
| GET | /api/v1/pokemon/{id} | Detalles |
| GET | /api/v1/pokemon/{id}/card | Tarjeta PNG o PDF |
| GET | /api/v1/pokemon/search | Buscar por nombre |
| GET | /api/v1/pokemon/type/{type} | Buscar por tipo |
| GET | /api/v1/pokemon/species/{id} | Datos de especie |

---

### ⚔️ **Equipos**
| Método | URL | Descripción |
|--------|------|------------|
| POST | /api/v1/teams | Crear equipo |
| GET | /api/v1/teams | Listar equipos |
| PUT | /api/v1/teams/{id} | Actualizar equipo |
| DELETE | /api/v1/teams/{id} | Eliminar |
| GET | /api/v1/teams/{id}/export | PDF con fichas |

---

## 🧪 Testing

Ejecutar tests:

```bash
pytest -v
```

Con cobertura:

```bash
pytest --cov
```

✔ Tests pasados: 33/33  
✔ 1 test skip por diseño  
✔ Cobertura: **88%**

---

## 🔐 Seguridad (resumen)

Detalles completos en **SECURITY.md**.

Incluye:
- JWT con expiración  
- Hash bcrypt  
- Rate limiting por endpoint  
- Validaciones Pydantic  
- CORS configurado  
- Logging avanzado de requests  

---

## 🚀 Mejoras Futuras

- Caché distribuido (Redis)
- Websockets para tiempo real
- Deploy en Render / Fly.io
- Sistema de amigos / social pokédex

---

## 📜 Licencia

Uso académico. Libre para estudio y aprendizaje.

---

**Desarrollado por:** *Oscar*  
Universidad Francisco de Vitoria

## 📹 Vídeo de la Presentación

Puedes ver la explicación completa de la API en este enlace:

👉 https://www.loom.com/share/05444f00998a4fe8a13d37a0e499ca6e
