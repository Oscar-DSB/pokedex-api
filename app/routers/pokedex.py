from typing import Literal, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import csv, io
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import StreamingResponse
from sqlmodel import select, Session
from sqlalchemy import func
from app.auth import get_current_user
from app.models import User, PokedexEntry
from app.database import get_session
from app.services.pokeapi_service import PokeAPIService
from app.schemas import PokedexCreate, PokedexUpdate, PokedexEntryOut

router = APIRouter(
    prefix="/api/v1/pokedex",
    tags=["pokedex"],
    dependencies=[Depends(get_current_user)]
)

service = PokeAPIService()

# ---------- helpers ----------
def _ensure_ownership(session: Session, entry_id: int, user_id: int) -> PokedexEntry:
    entry = session.exec(
        select(PokedexEntry).where(PokedexEntry.id == entry_id, PokedexEntry.user_id == user_id)
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada no encontrada o no pertenece al usuario")
    return entry

def _validate_pokemon_exists(pokemon_id: int) -> dict:
    # Llama a PokeAPI (usa tu servicio con caché)
    try:
        return service.get_pokemon(pokemon_id)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=400, detail="pokemon_id no existe en PokeAPI")
        raise

# ---------- POST: crear ----------
@router.post("", response_model=PokedexEntryOut, summary="Añade Pokémon a la Pokédex del usuario")
def create_pokedex_entry(
    body: PokedexCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 1) Validar que existe en PokeAPI
    poke = _validate_pokemon_exists(body.pokemon_id)

    # 2) Evitar duplicados para el mismo usuario
    exists = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.user_id == user.id,
            PokedexEntry.pokemon_id == body.pokemon_id
        )
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Este Pokémon ya está en tu Pokédex")

    # 3) Crear
    entry = PokedexEntry(
        user_id=user.id,
        pokemon_id=body.pokemon_id,
        pokemon_name=poke.get("name"),  # nos permite ordenar por nombre sin pedir PokeAPI
        nickname=body.nickname,
        is_captured=body.is_captured,
        capture_date=datetime.utcnow() if body.is_captured else None,
        favorite=False,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

# ---------- GET listado con filtros/orden/paginación ----------
@router.get("", response_model=list[PokedexEntryOut], summary="Lista la Pokédex del usuario")
def list_pokedex(
    captured: Optional[bool] = Query(None),
    favorite: Optional[bool] = Query(None),
    sort: Literal["pokemon_id", "capture_date", "pokemon_name"] = Query("pokemon_id"),
    order: Literal["asc", "desc"] = Query("asc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = select(PokedexEntry).where(PokedexEntry.user_id == user.id)

    if captured is not None:
        q = q.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        q = q.where(PokedexEntry.favorite == favorite)

    order_col = {
        "pokemon_id": PokedexEntry.pokemon_id,
        "capture_date": PokedexEntry.capture_date,
        "pokemon_name": PokedexEntry.pokemon_name,
    }[sort]

    q = q.order_by(order_col.asc() if order == "asc" else order_col.desc())
    q = q.offset(offset).limit(limit)

    items = session.exec(q).all()
    return items

# ---------- PATCH: actualizar (solo propietario) ----------
@router.patch("/{entry_id}", response_model=PokedexEntryOut, summary="Actualiza una entrada de la Pokédex")
def update_pokedex_entry(
    entry_id: int = Path(..., ge=1),
    body: PokedexUpdate = ...,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = _ensure_ownership(session, entry_id, user.id)

    # Actualizaciones parciales
    if body.is_captured is not None:
        entry.is_captured = body.is_captured
        # si ahora está capturado y no tenía fecha, ponla si no viene dada
        if entry.is_captured and entry.capture_date is None and body.capture_date is None:
            entry.capture_date = datetime.utcnow()

    if body.capture_date is not None:
        entry.capture_date = body.capture_date

    if body.nickname is not None:
        entry.nickname = body.nickname

    if body.favorite is not None:
        entry.favorite = body.favorite

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

# ---------- DELETE: eliminar (solo propietario) ----------
@router.delete("/{entry_id}", status_code=204, summary="Elimina una entrada de la Pokédex")
def delete_pokedex_entry(
    entry_id: int = Path(..., ge=1),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = _ensure_ownership(session, entry_id, user.id)
    session.delete(entry)
    session.commit()
    return None

def _fmt_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    # Sin zonas horarias: simple y claro
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

@router.get("/export", summary="Exporta la Pokédex del usuario en CSV o PDF")
def export_pokedex(
    format: Literal["csv", "pdf"] = Query("csv", description="Formato de exportación"),
    captured: Optional[bool] = Query(None, description="Filtrar por capturados"),
    favorite: Optional[bool] = Query(None, description="Filtrar por favoritos"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 1) Datos
    q = select(PokedexEntry).where(PokedexEntry.user_id == user.id)
    if captured is not None:
        q = q.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        q = q.where(PokedexEntry.favorite == favorite)
    q = q.order_by(PokedexEntry.pokemon_id.asc())
    rows = session.exec(q).all()

    # 2) CSV (bonito para Excel)
    if format == "csv":
        buf = io.StringIO(newline="")
        w = csv.writer(
            buf,
            delimiter=";",          # Excel ES
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\r\n"   # CRLF
        )
        w.writerow(["ID", "Nombre", "Apodo", "Capturado", "Favorito", "Fecha captura (UTC)"])
        for r in rows:
            w.writerow([
                r.pokemon_id,
                (r.pokemon_name or "").capitalize(),
                (r.nickname or ""),
                "Sí" if r.is_captured else "No",
                "★" if r.favorite else "",
                _fmt_dt(r.capture_date),
            ])
        data = buf.getvalue().encode("utf-16")
        filename = f"pokedex_{user.username}.csv"
        return StreamingResponse(io.BytesIO(data),
                                 media_type="text/csv; charset=utf-16",
                                 headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'})

    # ---------- PDF estilo Pokédex DS (sin reportlab) ----------
    from PIL import Image, ImageDraw, ImageFont
    import httpx

    def _load_sprite(pokemon_id: int) -> Image.Image:
        """Carga sprite oficial de PokeAPI. Si falla, devuelve un placeholder."""
        url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
        try:
            with httpx.Client(timeout=8) as client:
                r = client.get(url)
                r.raise_for_status()
                spr = Image.open(io.BytesIO(r.content)).convert("RGBA")
                return spr
        except Exception:
            # cuadrado gris si no hay red
            ph = Image.new("RGBA", (96, 96), (200, 200, 200, 255))
            d = ImageDraw.Draw(ph)
            d.line((0, 0, 96, 96), fill=(160, 160, 160), width=3)
            d.line((96, 0, 0, 96), fill=(160, 160, 160), width=3)
            return ph

    def _text_w(draw, text, font):
        # compat Pil
        if hasattr(draw, "textlength"):
            return draw.textlength(text, font=font)
        return draw.textbbox((0, 0), text, font=font)[2]

    def _draw_grid(draw: ImageDraw.ImageDraw, W: int, H: int, step: int = 16, color=(230, 230, 230)):
        for x in range(0, W, step):
            draw.line((x, 0, x, H), fill=color)
        for y in range(0, H, step):
            draw.line((0, y, W, y), fill=color)

    # Colores “DS vibes”
    C_HEADER = (27, 102, 201)  # azul cabecera
    C_PANEL = (245, 245, 245)  # panel lateral
    C_LINE = (200, 200, 200)  # líneas
    C_SELECT = (255, 77, 77)  # celda seleccionada
    C_TEXT = (30, 30, 30)

    # Página base
    W, H = (900, 1200)

    # Intenta fuente del sistema; si no, default
    try:
        FONT_TITLE = ImageFont.truetype("arial.ttf", 34)
        FONT_UI = ImageFont.truetype("arial.ttf", 18)
        FONT_NUM = ImageFont.truetype("arial.ttf", 16)
    except:
        FONT_TITLE = ImageFont.load_default()
        FONT_UI = ImageFont.load_default()
        FONT_NUM = ImageFont.load_default()

    pages: list[Image.Image] = []

    for idx, r in enumerate(rows):
        page = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(page)

        # Fondo cuadriculado sutil
        _draw_grid(draw, W, H, step=16, color=(236, 236, 236))

        # Cabecera
        draw.rectangle((0, 0, W, 90), fill=C_HEADER)
        title = f"Pokédex de {user.username}"
        tw = _text_w(draw, title, FONT_TITLE)
        draw.text(((W - tw) // 2, 26), title, fill="white", font=FONT_TITLE)

        # Panel lateral (lista)
        left = 40
        top = 120
        panel_w = 320
        panel_h = H - top - 60
        draw.rounded_rectangle((left, top, left + panel_w, top + panel_h), radius=16, fill=C_PANEL, outline=C_LINE,
                               width=2)

        # Cabecera panel
        draw.text((left + 16, top + 12), "Pokédex Nacional", fill=C_TEXT, font=FONT_UI)
        y = top + 48
        row_h = 36

        # Lista de 12 slots con selección en la entrada actual (estética)
        # Mostramos un “window” de ids alrededor del actual
        base_id = max(1, (r.pokemon_id // 12) * 12 - 1)
        items = [base_id + i for i in range(1, 13)]
        for pid in items:
            # celda
            cell = (left + 8, y, left + panel_w - 8, y + row_h)
            # ¿seleccionado?
            if pid == r.pokemon_id:
                draw.rounded_rectangle(cell, radius=8, fill=C_SELECT, outline=C_LINE)
                text_col = "white"
                mark = "● "
            else:
                draw.rounded_rectangle(cell, radius=8, fill="white", outline=C_LINE)
                text_col = C_TEXT
                mark = "  "

            # número + nombre aproximado si lo tenemos
            num_txt = f"{pid:03d} "
            draw.text((cell[0] + 8, y + 9), mark + num_txt, fill=text_col, font=FONT_NUM)
            # si coincide con actual, ponemos el nombre real
            if pid == r.pokemon_id:
                name = (r.pokemon_name or "").capitalize()
                draw.text((cell[0] + 80, y + 9), name if name else "—", fill=text_col, font=FONT_NUM)

            y += row_h + 6

        # Panel derecho (detalle)
        right_x = left + panel_w + 24
        right_w = W - right_x - 40
        draw.rounded_rectangle((right_x, top, right_x + right_w, H - 60), radius=16, fill="white", outline=C_LINE,
                               width=2)

        # Sprite a la derecha y datos
        spr = _load_sprite(r.pokemon_id)
        # escalar sprite suavemente
        scale = 3 if spr.width <= 64 else 2
        spr_big = spr.resize((spr.width * scale, spr.height * scale), Image.NEAREST)
        # posición sprite
        sx = right_x + right_w - spr_big.width - 40
        sy = top + 40
        page.paste(spr_big, (sx, sy), spr_big)

        # Datos a la izquierda del sprite
        dx = right_x + 28
        dy = top + 40
        draw.text((dx, dy), f"#{r.pokemon_id}  {(r.pokemon_name or '').capitalize()}", fill=C_TEXT, font=FONT_UI)
        dy += 34
        draw.line((dx, dy, dx + right_w - 56, dy), fill=C_LINE, width=1)
        dy += 16

        draw.text((dx, dy), f"Apodo: {(r.nickname or '-')}", fill=C_TEXT, font=FONT_UI)
        dy += 28
        draw.text((dx, dy), f"Capturado: {'Sí' if r.is_captured else 'No'}", fill=C_TEXT, font=FONT_UI)
        dy += 28
        draw.text((dx, dy), f"Favorito: {'★' if r.favorite else '—'}", fill=C_TEXT, font=FONT_UI)
        dy += 28

        # Fecha (UTC simple, como dejaste)
        cap = r.capture_date.strftime("%Y-%m-%d %H:%M:%S UTC") if r.capture_date else "-"
        draw.text((dx, dy), f"Fecha captura: {cap}", fill=C_TEXT, font=FONT_UI)
        dy += 28

        # pie de página
        foot = f"{idx + 1}/{len(rows)}"
        draw.text((W - 40 - _text_w(draw, foot, FONT_NUM), H - 40), foot, fill=(120, 120, 120), font=FONT_NUM)

        pages.append(page)

    # Guardamos todas las páginas en un único PDF
    out = io.BytesIO()
    if len(pages) == 1:
        pages[0].save(out, format="PDF")
    else:
        pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:])
    out.seek(0)
    filename = f"pokedex_{user.username}.pdf"
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
    )
def _capture_streak_days(rows: list[PokedexEntry]) -> int:
    """Racha de días consecutivos con al menos una captura hasta 'hoy' (UTC).
       Si hoy no hay captura, la racha es 0."""
    # Fechas únicas (UTC, solo capturados con fecha)
    days = {
        (r.capture_date.astimezone(timezone.utc).date()
         if r.capture_date.tzinfo else r.capture_date.replace(tzinfo=timezone.utc).date())
        for r in rows
        if r.is_captured and r.capture_date is not None
    }
    if not days:
        return 0

    today = datetime.now(tz=timezone.utc).date()
    # Si hoy no hay captura, racha = 0
    if today not in days:
        return 0

    # Cuenta hacia atrás mientras existan días consecutivos
    streak = 0
    d = today
    while d in days:
        streak += 1
        d = d - timedelta(days=1)
    return streak

@router.get("/stats", summary="Estadísticas de la Pokédex del usuario")
def pokedex_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    # Todas las entradas del usuario
    q = select(PokedexEntry).where(PokedexEntry.user_id == user.id)
    rows = session.exec(q).all()

    total_pokemon = len(rows)
    captured = sum(1 for r in rows if r.is_captured)
    favorites = sum(1 for r in rows if r.favorite)

    completion_percentage = round((captured / total_pokemon) * 100, 1) if total_pokemon else 0.0

    # Tipo más común (usamos PokeAPIService con caché para no machacar la red)
    type_counter: Counter[str] = Counter()
    for r in rows:
        try:
            p = service.get_pokemon(r.pokemon_id)  # si prefieres tolerante a fallos: get_pokemon_relaxed
            types = [t["type"]["name"] for t in p.get("types", [])]
            type_counter.update(types)
        except Exception:
            # si algo falla (red, etc.), ignora ese pokémon
            continue
    most_common_type: Optional[str] = type_counter.most_common(1)[0][0] if type_counter else None

    capture_streak_days = _capture_streak_days(rows)

    return {
        "total_pokemon": total_pokemon,
        "captured": captured,
        "favorites": favorites,
        "completion_percentage": completion_percentage,
        "most_common_type": most_common_type,
        "capture_streak_days": capture_streak_days,
    }