# app/routers/pokemon.py
import logging

from fastapi import APIRouter, Depends, Path, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Literal
import io
from app.rate_limiter import limiter
import httpx
from PIL import Image, ImageDraw, ImageFont

from app.auth import get_current_user
from app.models import User
from app.services.pokeapi_service import PokeAPIService

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/pokemon",
    tags=["pokemon"],
    dependencies=[Depends(get_current_user)]  # 🔒 requiere token
)
service = PokeAPIService()

# ------------------ Helpers ------------------

def _type_theme(primary_type: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Devuelve (fondo, header) según el tipo principal."""
    t = (primary_type or "").lower()
    # fondo, header
    themes = {
        "electric": ((253, 242, 186), (250, 208, 44)),
        "fire":     ((255, 221, 204), (255, 133,  82)),
        "water":    ((206, 230, 255), ( 68, 149, 255)),
        "grass":    ((209, 245, 212), ( 95, 199, 110)),
        "psychic":  ((240, 209, 252), (194,  84, 255)),
        "fighting": ((240, 208, 192), (199,  98,  70)),
        "dragon":   ((210, 226, 252), ( 99, 127, 199)),
        "ice":      ((220, 246, 252), ( 91, 189, 214)),
        "rock":     ((232, 222, 205), (183, 161, 121)),
        "ground":   ((235, 220, 188), (201, 159,  83)),
        "bug":      ((226, 242, 191), (166, 199,  58)),
        "ghost":    ((219, 214, 243), (116, 108, 171)),
        "dark":     ((214, 210, 206), ( 87,  82,  78)),
        "fairy":    ((254, 216, 244), (234, 113, 213)),
        "steel":    ((221, 230, 236), (144, 160, 174)),
        "poison":   ((229, 210, 239), (153,  94, 173)),
        "flying":   ((224, 236, 255), (130, 170, 255)),
        "normal":   ((235, 232, 223), (187, 177, 160)),
    }
    return themes.get(t, ((240, 240, 240), (200, 200, 200)))

def _rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    except Exception:
        # Fallback para Pillow muy antiguo
        draw.rectangle(box, fill=fill, outline=outline, width=width)

def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width_px: int):
    """Word wrap usando textbbox."""
    if not text:
        return []
    words = text.replace("\n", " ").replace("\f", " ").split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        l, t, r, b = draw.textbbox((0, 0), test, font=font)
        if (r - l) > max_width_px and line:
            lines.append(line); line = w
        else:
            line = test
    if line: lines.append(line)
    return lines

def _type_emoji(primary_type: str) -> str:
    """Iconito simple por tipo (opcional)."""
    m = {
        "electric": "⚡", "fire": "🔥", "water": "💧", "grass": "🌿", "psychic": "💫",
        "fighting": "🥊", "dragon": "🐉", "ice": "❄️", "rock": "🪨", "ground": "🏜️",
        "bug": "🐞", "ghost": "👻", "dark": "🌑", "fairy": "✨", "steel": "⚙️",
        "poison": "☠️", "flying": "🕊️", "normal": "●",
    }
    return m.get((primary_type or "").lower(), "●")

def _bar(draw: ImageDraw.ImageDraw, x, y, value, max_value=120, w=180, h=12, fill=(90, 200, 90), bg=(220, 220, 220)):
    """Barra horizontal para stats (valor mapeado a ancho)."""
    _rounded(draw, (x, y, x+w, y+h), radius=6, fill=bg, outline=None)
    pct = max(0, min(1, value / max_value))
    if pct > 0:
        _rounded(draw, (x, y, x+int(w*pct), y+h), radius=6, fill=fill, outline=None)

# ------------------ Render estilo TCG ------------------

def _render_card_tcg_png(poke: dict, species: dict) -> bytes:
    """
    Renderiza un 'look TCG' sencillo:
    - marco con esquinas redondeadas
    - header coloreado con nombre y HP
    - sprite en marco
    - 'movimientos': mostramos 4 stats con barras
    - pie con tipos, habilidades y descripción
    """
    # ---------- datos ----------
    name = poke.get("name","").capitalize()
    pid  = poke.get("id")
    sprite_url = poke.get("sprites",{}).get("front_default")
    types_list = [t["type"]["name"] for t in poke.get("types",[])]
    primary_type = types_list[0] if types_list else "normal"
    abilities = [a["ability"]["name"].replace("-"," ").title() for a in poke.get("abilities",[])]
    stats = {s["stat"]["name"]: s["base_stat"] for s in poke.get("stats",[])}

    # descripción ES → EN → fallback
    desc = ""
    for e in species.get("flavor_text_entries", []):
        lang = e.get("language",{}).get("name")
        if lang in ("es","es-es"): desc = e.get("flavor_text",""); break
        if not desc and lang=="en": desc = e.get("flavor_text","")
    desc = (desc or "Sin descripción disponible.").replace("\n"," ").replace("\f"," ").strip()

    # ---------- canvas ----------
    W, H = 720, 1020     # proporción carta
    img = Image.new("RGB", (W,H), (230,230,230))
    draw = ImageDraw.Draw(img)
    font_title = ImageFont.load_default()
    font = ImageFont.load_default()

    bg, header = _type_theme(primary_type)

    # marco exterior
    _rounded(draw, (20,20,W-20,H-20), radius=36, fill=bg, outline=(60,60,60), width=3)

    # header
    _rounded(draw, (36,36,W-36,120), radius=20, fill=header, outline=(50,50,50), width=2)
    draw.text((56, 56), f"{_type_emoji(primary_type)}  {name}", fill=(20,20,20), font=font_title)
    # HP a la derecha (estética TCG)
    hp = stats.get("hp","-")
    draw.text((W-160, 56), f"HP {hp}", fill=(20,20,20), font=font_title)

    # marco sprite
    _rounded(draw, (56,140, 56+280, 140+280), radius=24, fill=(255,255,255), outline=(120,120,120), width=2)

    # pega sprite
    if sprite_url:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(sprite_url); r.raise_for_status()
                sp = Image.open(io.BytesIO(r.content)).convert("RGBA")
                sp.thumbnail((240,240))
                # centrado en el marco
                ox = 56 + (280 - sp.width)//2
                oy = 140 + (280 - sp.height)//2
                img.paste(sp, (ox, oy), sp)
        except Exception:
            pass

    # caja 'movimientos'/stats
    _rounded(draw, (360, 140, W-56, 140+220), radius=16, fill=(255,255,255), outline=(150,150,150), width=2)
    draw.text((380, 154), "Estadísticas", fill=(30,30,30), font=font_title)
    y = 184
    for label in ("attack","defense","speed"):
        val = stats.get(label, 0)
        draw.text((380, y), f"{label.title()} ", fill=(30,30,30), font=font)
        _bar(draw, 480, y, val, max_value=150, w=180, h=12)
        draw.text((670, y), str(val), fill=(30,30,30), font=font)
        y += 36

    # caja info abajo sprite (tipos y habilidades)
    _rounded(draw, (56, 440, W-56, 580), radius=16, fill=(255,255,255), outline=(150,150,150), width=2)
    draw.text((76, 456), f"Tipos: {', '.join(t.capitalize() for t in types_list) or '-'}", fill=(30,30,30), font=font)
    draw.text((76, 486), f"Habilidades: {', '.join(abilities) or '-'}", fill=(30,30,30), font=font)

    # descripción (bloque grande)
    _rounded(draw, (56, 600, W-56, H-56), radius=16, fill=(255,255,255), outline=(150,150,150), width=2)
    draw.text((76, 616), "Descripción", fill=(30,30,30), font=font_title)
    text_lines = _wrap_text(draw, desc, font, max_width_px=W-56-76-20)
    ty = 646
    for ln in text_lines[:18]:
        draw.text((76, ty), ln, fill=(35,35,35), font=font)
        ty += 24

    # numerito id y pie
    draw.text((W-140, H-80), f"#{pid}", fill=(60,60,60), font=font)

    # export
    buf = io.BytesIO()
    img.save(buf, format="PNG"); buf.seek(0)
    return buf.read()



@router.get("/{id_or_name}/card", summary="Genera una ficha estilo TCG (PNG o PDF)")
def get_pokemon_card(
    id_or_name: str = Path(..., description="ID o nombre del Pokémon"),
    format: Literal["png", "pdf"] = Query("png", description="Formato de salida"),
    user: User = Depends(get_current_user),
):
    try:
        poke = service.get_pokemon(id_or_name)
        species = service.get_species(id_or_name)
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception(f"Error inesperado con '{id_or_name}'")
        raise HTTPException(status_code=500, detail="Unexpected error")

    # 🔸 Siempre usa TCG (sin parámetro style)
    png_bytes = _render_card_tcg_png(poke, species)

    if format == "png":
        filename = f'{poke.get("name","pokemon")}_card.png'
        return StreamingResponse(
            io.BytesIO(png_bytes),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
        )
    else:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PDF")
        out.seek(0)
        filename = f'{poke.get("name","pokemon")}_card.pdf'
        return StreamingResponse(
            out,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
        )

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}


@router.get("/search", summary="Busca Pokémon por nombre (proxy PokeAPI)")
@limiter.limit("30/minute")
def search_pokemon_by_name(
    request: Request,
    name: str = Query(..., min_length=2, description="Substring del nombre"),
    limit: int = Query(20, ge=1, le=20),
    offset: int = Query(0, ge=0),
):
    result = service.search_pokemon_by_name(name=name, limit=limit, offset=offset)

    if not result:
        raise HTTPException(status_code=404, detail="No se encontraron Pokémon")

    return result

@router.get("/{id_or_name}")
def get_pokemon(id_or_name: str, ):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/{id_or_name}")
    try:
        data = service.get_pokemon(id_or_name)
        logger.info(f"Pokémon encontrado: {data['name']} (ID {data['id']})")
        return {
        "id": data["id"],
        "name": data["name"].capitalize(),
        "sprites": data.get("sprites", {}),  # estructura completa de sprites
        "types": [t["type"]["name"] for t in data.get("types", [])],
        "abilities": [a["ability"]["name"] for a in data.get("abilities", [])],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])},
        }
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception(f"Error inesperado con '{id_or_name}'")
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("")
@router.get("/", include_in_schema=False)
def search_pokemons(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon?limit={limit}&offset={offset}")
    try:
        data = service.search_pokemons(limit=limit, offset=offset)
        results = []
        for item in data.get("results", []):
            url = item["url"].rstrip("/")
            poke_id = int(url.split("/")[-1])
            results.append({
                "id": poke_id,
                "name": item["name"].capitalize(),
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
            })
        logger.info(f"Listado generado: {len(results)} elementos")
        return {"count": data.get("count", len(results)), "results": results}
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception(f"Error inesperado")
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/type/{type_name}")
def get_pokemon_by_type(
    type_name: str = Path(..., description="Tipo de Pokémon (fire, water, grass, etc.)")
):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/type/{type_name}")
    try:
        data = service.get_pokemon_by_type(type_name)
        results = []
        for item in data.get("pokemon", []):
            pokemon = item["pokemon"]
            url = pokemon["url"].rstrip("/")
            poke_id = int(url.split("/")[-1])
            results.append({
                "id": poke_id,
                "name": pokemon["name"].capitalize(),
                "sprite": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png"
            })
        logger.info(f"Tipo '{data['name']}' → {len(results)} elementos")
        return {"type": data["name"].capitalize(), "count": len(results), "results": results}
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception(f"Error inesperado")
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/species/{id_or_name}")
def get_pokemon_species(id_or_name: str):
    logger.info(f"Solicitud recibida: GET /api/v1/pokemon/species/{id_or_name}")
    try:
        data = service.get_species(id_or_name)
        species_info = {
            "id": data.get("id"),
            "name": data.get("name", "").capitalize(),
            "color": (data.get("color") or {}).get("name"),
            "habitat": (data.get("habitat") or {}).get("name"),
            "shape": (data.get("shape") or {}).get("name"),
            "is_legendary": data.get("is_legendary", False),
            "is_mythical": data.get("is_mythical", False),
        }
        # Descripción: prioriza ES y cae a EN si no hay
        desc = None
        for entry in data.get("flavor_text_entries", []):
            if entry["language"]["name"] == "es":
                desc = entry["flavor_text"]; break
        if desc is None:
            for entry in data.get("flavor_text_entries", []):
                if entry["language"]["name"] == "en":
                    desc = entry["flavor_text"]; break
        if desc:
            species_info["description"] = desc.replace("\n", " ").replace("\f", " ")
        logger.info(f"Especie '{species_info['name']}' obtenida (ID {species_info['id']})")
        return species_info
    except HTTPException as e:
        raise e
    except Exception:
        logger.exception(f"Error inesperado con '{id_or_name}'")
        raise HTTPException(status_code=500, detail="Unexpected error")
