from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Any, Dict, Optional, Literal
import io, csv, logging

from app.auth import get_current_user
from app.database import get_session
from app.models import User, PokedexEntry, TeamMember
from app.schemas import PokedexCreate, PokedexUpdate, PokedexEntryOut
from app.services.pokeapi_service import PokeAPIService
from app.rate_limiter import limiter

logger = logging.getLogger("pokedex_api")

router = APIRouter(prefix="/pokedex", tags=["pokedex"])
service = PokeAPIService()


# -------------------------------
# POST /api/v1/pokedex
# -------------------------------
@router.post("", response_model=PokedexEntryOut)
@limiter.limit("30/minute")
def add_pokedex_entry(
    request: Request,
    body: PokedexCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} → Añadiendo Pokémon ID {body.pokemon_id}")
    existing = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.user_id == user.id,
            PokedexEntry.pokemon_id == body.pokemon_id,
        )
    ).first()
    if existing:
        logger.warning(f"{user.username} intentó duplicar {body.pokemon_id}")
        raise HTTPException(status_code=400, detail="Ya tienes este Pokémon")

    poke_data = service.get_pokemon(body.pokemon_id)
    entry = PokedexEntry(
        user_id=user.id,
        pokemon_id=body.pokemon_id,
        pokemon_name=poke_data.get("name"),
        nickname=body.nickname,
        is_captured=body.is_captured,
        capture_date=datetime.utcnow(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    logger.info(f"{user.username} capturó {entry.pokemon_name}")
    return entry

# -------------------------------
# GET /api/v1/pokedex
# -------------------------------
@router.get("", response_model=list[PokedexEntryOut])
@limiter.limit("100/minute")
def list_pokedex(
    request: Request,
    captured: bool | None = Query(None),
    favorite: bool | None = Query(None),
    sort: str = Query("pokemon_id"),
    order: str = Query("asc"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} → Consulta Pokédex (filtros cap={captured}, fav={favorite})")
    query = select(PokedexEntry).where(PokedexEntry.user_id == user.id)
    if captured is not None:
        query = query.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        query = query.where(PokedexEntry.favorite == favorite)

    if sort not in {"pokemon_id", "capture_date", "pokemon_name"}:
        sort = "pokemon_id"

    if order == "desc":
        query = query.order_by(getattr(PokedexEntry, sort).desc())
    else:
        query = query.order_by(getattr(PokedexEntry, sort))

    return session.exec(query).all()

# -------------------------------
# PATCH /api/v1/pokedex/{entry_id}
# -------------------------------
@router.patch("/{entry_id}", response_model=PokedexEntryOut)
@limiter.limit("30/minute")
def update_pokedex_entry(
    request: Request,
    entry_id: int,
    body: PokedexUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = session.exec(
        select(PokedexEntry).where(PokedexEntry.id == entry_id, PokedexEntry.user_id == user.id)
    ).first()
    if not entry:
        logger.warning(f"{user.username} intentó modificar entrada inexistente {entry_id}")
        raise HTTPException(status_code=404, detail="Entrada no encontrada")

    logger.info(f"{user.username} actualiza entrada {entry.pokemon_name}")
    for field, value in body.dict(exclude_unset=True).items():
        setattr(entry, field, value)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

# -------------------------------
# DELETE /api/v1/pokedex/{entry_id}
# -------------------------------
@router.delete("/{entry_id}")
def delete_pokedex_entry(entry_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    logger.info(f"{user.username} → Eliminando entrada {entry_id}")

    entry = session.get(PokedexEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entrada no encontrada")

    # ✅ Primero, eliminar vínculos en teammember
    team_links = session.exec(
        select(TeamMember).where(TeamMember.pokedex_entry_id == entry.id)
    ).all()
    for link in team_links:
        session.delete(link)

    # ✅ Luego, eliminar la entrada de la Pokédex
    session.delete(entry)
    session.commit()

    logger.info(f"{user.username} eliminó {entry.pokemon_name} correctamente")
    return {"detail": f"Entrada {entry_id} eliminada correctamente"}


from typing import Literal, Optional

def _fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"

@router.get("/export", summary="Exporta la Pokédex del usuario en CSV o PDF")
def export_pokedex(
    format: Literal["csv", "pdf"] = Query("csv", description="Formato de exportación"),
    captured: Optional[bool] = Query(None, description="Filtrar por capturados"),
    favorite: Optional[bool] = Query(None, description="Filtrar por favoritos"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Exporta la Pokédex del usuario autenticado como CSV o PDF con diseño estilo DS."""
    # 1) Filtrar datos
    q = select(PokedexEntry).where(PokedexEntry.user_id == user.id)
    if captured is not None:
        q = q.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        q = q.where(PokedexEntry.favorite == favorite)
    q = q.order_by(PokedexEntry.pokemon_id.asc())
    rows = session.exec(q).all()

    if not rows:
        raise HTTPException(400, "No hay entradas para exportar con esos filtros.")

    # 2) CSV (compatible con Excel en español)
    if format == "csv":
        buf = io.StringIO(newline="")
        w = csv.writer(
            buf,
            delimiter=",",  # ✅ cambia a coma
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\r\n"
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
        # ✅ BOM + UTF-8
        data = ("\ufeff" + buf.getvalue()).encode("utf-8")
        filename = f"pokedex_{user.username}.csv"
        logger.info(f"{user.username} exporta Pokédex (CSV, {len(rows)} entradas)")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
        )

    # 3) PDF estilo DS
    from PIL import Image, ImageDraw, ImageFont
    import httpx

    def _load_sprite(pokemon_id: int) -> Image.Image:
        url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"
        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.get(url)
                r.raise_for_status()
                return Image.open(io.BytesIO(r.content)).convert("RGBA")
        except Exception:
            ph = Image.new("RGBA", (96, 96), (180, 180, 180, 255))
            d = ImageDraw.Draw(ph)
            d.line((0, 0, 96, 96), fill=(150, 150, 150), width=3)
            d.line((96, 0, 0, 96), fill=(150, 150, 150), width=3)
            return ph

    def _text_w(draw, text, font):
        if hasattr(draw, "textlength"):
            return draw.textlength(text, font=font)
        return draw.textbbox((0, 0), text, font=font)[2]

    def _draw_grid(draw, W, H, step=16, color=(236, 236, 236)):
        for x in range(0, W, step):
            draw.line((x, 0, x, H), fill=color)
        for y in range(0, H, step):
            draw.line((0, y, W, y), fill=color)

    # Colores estilo DS
    C_HEADER = (27, 102, 201)
    C_PANEL = (245, 245, 245)
    C_LINE = (200, 200, 200)
    C_SELECT = (255, 77, 77)
    C_TEXT = (30, 30, 30)

    W, H = (900, 1200)

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
        _draw_grid(draw, W, H, step=16)

        # Cabecera
        draw.rectangle((0, 0, W, 90), fill=C_HEADER)
        title = f"Pokédex de {user.username}"
        tw = _text_w(draw, title, FONT_TITLE)
        draw.text(((W - tw) // 2, 26), title, fill="white", font=FONT_TITLE)

        # Panel izquierdo
        left, top = 40, 120
        panel_w, panel_h = 320, H - top - 60
        draw.rounded_rectangle((left, top, left + panel_w, top + panel_h),
                               radius=16, fill=C_PANEL, outline=C_LINE, width=2)
        draw.text((left + 16, top + 12), "Pokédex Nacional", fill=C_TEXT, font=FONT_UI)
        y = top + 48
        row_h = 36
        base_id = max(1, (r.pokemon_id // 12) * 12 - 1)
        items = [base_id + i for i in range(1, 13)]
        for pid in items:
            cell = (left + 8, y, left + panel_w - 8, y + row_h)
            if pid == r.pokemon_id:
                draw.rounded_rectangle(cell, radius=8, fill=C_SELECT, outline=C_LINE)
                color = "white"
                mark = "● "
            else:
                draw.rounded_rectangle(cell, radius=8, fill="white", outline=C_LINE)
                color = C_TEXT
                mark = "  "
            num_txt = f"{pid:03d} "
            draw.text((cell[0] + 8, y + 9), mark + num_txt, fill=color, font=FONT_NUM)
            if pid == r.pokemon_id:
                name = (r.pokemon_name or "").capitalize()
                draw.text((cell[0] + 80, y + 9), name if name else "—", fill=color, font=FONT_NUM)
            y += row_h + 6

        # Panel derecho
        right_x = left + panel_w + 24
        right_w = W - right_x - 40
        draw.rounded_rectangle((right_x, top, right_x + right_w, H - 60),
                               radius=16, fill="white", outline=C_LINE, width=2)

        # Sprite
        spr = _load_sprite(r.pokemon_id)
        scale = 3 if spr.width <= 64 else 2
        spr_big = spr.resize((spr.width * scale, spr.height * scale), Image.NEAREST)
        sx = right_x + right_w - spr_big.width - 40
        sy = top + 40
        page.paste(spr_big, (sx, sy), spr_big)

        # Datos
        dx, dy = right_x + 28, top + 40
        draw.text((dx, dy), f"#{r.pokemon_id} {(r.pokemon_name or '').capitalize()}", fill=C_TEXT, font=FONT_UI)
        dy += 34
        draw.line((dx, dy, dx + right_w - 56, dy), fill=C_LINE)
        dy += 16
        draw.text((dx, dy), f"Apodo: {(r.nickname or '-')}", fill=C_TEXT, font=FONT_UI); dy += 28
        draw.text((dx, dy), f"Capturado: {'Sí' if r.is_captured else 'No'}", fill=C_TEXT, font=FONT_UI); dy += 28
        draw.text((dx, dy), f"Favorito: {'★' if r.favorite else '—'}", fill=C_TEXT, font=FONT_UI); dy += 28
        cap = r.capture_date.strftime("%Y-%m-%d %H:%M:%S UTC") if r.capture_date else "-"
        draw.text((dx, dy), f"Fecha captura: {cap}", fill=C_TEXT, font=FONT_UI)
        dy += 28

        foot = f"{idx + 1}/{len(rows)}"
        draw.text((W - 40 - _text_w(draw, foot, FONT_NUM), H - 40), foot, fill=(120, 120, 120), font=FONT_NUM)

        pages.append(page)

    out = io.BytesIO()
    if len(pages) == 1:
        pages[0].save(out, format="PDF")
    else:
        pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:])
    out.seek(0)
    filename = f"pokedex_{user.username}.pdf"
    logger.info(f"{user.username} exporta Pokédex (PDF, {len(rows)} páginas)")
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
# -------------------------------
#  Cálculo de racha de capturas
# -------------------------------
def _capture_streak_days(rows: list[PokedexEntry]) -> int:
    """Devuelve la racha de días consecutivos con al menos una captura (UTC)."""
    days = {
        (
            r.capture_date.astimezone(timezone.utc).date()
            if r.capture_date.tzinfo
            else r.capture_date.replace(tzinfo=timezone.utc).date()
        )
        for r in rows
        if r.is_captured and r.capture_date is not None
    }

    if not days:
        return 0

    today = datetime.now(tz=timezone.utc).date()
    if today not in days:
        return 0

    streak = 0
    d = today
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return streak

# -----------------------------------------
#  GET /api/v1/pokedex/stats
# -----------------------------------------
@router.get("/stats", summary="Estadísticas de la Pokédex del usuario")
def pokedex_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Devuelve estadísticas generales y de actividad del usuario."""
    q = select(PokedexEntry).where(PokedexEntry.user_id == user.id)
    rows = session.exec(q).all()

    total_pokemon = len(rows)
    captured = sum(1 for r in rows if r.is_captured)
    favorites = sum(1 for r in rows if r.favorite)
    completion_percentage = round((captured / total_pokemon) * 100, 1) if total_pokemon else 0.0

    # Tipo más común
    type_counter: Counter[str] = Counter()
    for r in rows:
        try:
            p = service.get_pokemon(r.pokemon_id)
            types = [t["type"]["name"] for t in p.get("types", [])]
            type_counter.update(types)
        except Exception:
            # si algo falla (red, timeout...), ignoramos ese Pokémon
            continue

    most_common_type: Optional[str] = type_counter.most_common(1)[0][0] if type_counter else None
    capture_streak_days = _capture_streak_days(rows)

    logger.info(
        f"{user.username} -> Stats: {captured}/{total_pokemon} capturados "
        f"({completion_percentage}%), racha {capture_streak_days} días"
    )

    return {
        "total_pokemon": total_pokemon,
        "captured": captured,
        "favorites": favorites,
        "completion_percentage": completion_percentage,
        "most_common_type": most_common_type,
        "capture_streak_days": capture_streak_days,
    }
