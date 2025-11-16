from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select, delete
from app.auth import get_current_user
from app.database import get_session
from app.models import User, Team, TeamMember, PokedexEntry
from app.schemas import TeamCreate, TeamUpdate, TeamOut
from app.rate_limiter import limiter
import logging, io, httpx
from app.services import service
from PIL import Image, ImageDraw, ImageFont
import statistics

logger = logging.getLogger("pokedex_api")
router = APIRouter(prefix="/teams", tags=["teams"])

# ------------------------------------------------
# 🧩 Crear equipo
# ------------------------------------------------
@router.post("", response_model=TeamOut)
@limiter.limit("20/minute")
def create_team(
    request: Request,
    body: TeamCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} crea un equipo: {body.name}")

    # ✅ FIX 1: validar nombre requerido
    if not body.name:
        raise HTTPException(status_code=422, detail="El nombre del equipo es obligatorio")

    team = Team(trainer_id=user.id, name=body.name, description=body.description or "")
    session.add(team)
    session.commit()
    session.refresh(team)

    # ✅ FIX 2: manejar pokemon_ids = None sin error
    for i, pid in enumerate(body.pokemon_ids or [], start=1):
        pokedex_entry = session.exec(
            select(PokedexEntry).where(
                PokedexEntry.user_id == user.id, PokedexEntry.pokemon_id == pid
            )
        ).first()
        if not pokedex_entry:
            raise HTTPException(status_code=400, detail=f"Pokémon ID {pid} no está en tu Pokédex")
        session.add(TeamMember(team_id=team.id, pokedex_entry_id=pokedex_entry.id, position=i))
    session.commit()
    logger.info(f"Equipo '{team.name}' creado con {len(body.pokemon_ids or [])} Pokémon")

    return TeamOut(id=team.id, name=team.name, description=team.description, members=[])

# ------------------------------------------------
# Listar equipos
# ------------------------------------------------
@router.get("", response_model=list[TeamOut])
@limiter.limit("50/minute")
def list_teams(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} lista sus equipos")

    # FIX 3: usar all() y no first()
    teams = (
        session.exec(
            select(Team)
            .options(joinedload(Team.members).joinedload(TeamMember.pokedex_entry))
            .where(Team.trainer_id == user.id)
        )
        .unique()
        .all()
    )

    return [
        TeamOut(
            id=t.id,
            name=t.name,
            description=t.description,
            members = [
                {
                    "pokemon_id": m.pokedex_entry.pokemon_id,
                    "pokemon_name": m.pokedex_entry.pokemon_name
                }
                for m in (t.members or [])
                if m.pokedex_entry is not None
            ],

        )
        for t in teams
    ]

# ------------------------------------------------
# Actualizar equipo
# ------------------------------------------------
@router.put("/{team_id}", response_model=TeamOut)
@limiter.limit("20/minute")
def update_team(
    request: Request,
    team_id: int,
    body: TeamUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} actualiza el equipo {team_id}")
    team = session.get(Team, team_id)
    if not team or team.trainer_id != user.id:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    if body.name:
        team.name = body.name
    if body.description is not None:
        team.description = body.description

    if body.pokemon_ids:
        if len(body.pokemon_ids) > 6:
            raise HTTPException(status_code=400, detail="Máximo 6 Pokémon por equipo")
        entries = session.exec(
            select(PokedexEntry).where(
                PokedexEntry.user_id == user.id,
                PokedexEntry.pokemon_id.in_(body.pokemon_ids)
            )
        ).all()
        if len(entries) != len(body.pokemon_ids):
            raise HTTPException(status_code=400, detail="Pokémon no válidos en tu Pokédex")

        session.exec(delete(TeamMember).where(TeamMember.team_id == team.id))
        for i, e in enumerate(entries, start=1):
            session.add(TeamMember(team_id=team.id, pokedex_entry_id=e.id, position=i))
    session.commit()
    session.refresh(team)
    return TeamOut(id=team.id, name=team.name, description=team.description, members=[])

# ------------------------------------------------
# Eliminar equipo
# ------------------------------------------------
@router.delete("/{team_id}")
@limiter.limit("20/minute")
def delete_team(
    request: Request,
    team_id: int = Path(..., ge=1),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} elimina el equipo {team_id}")
    team = session.exec(select(Team).where(Team.id == team_id, Team.trainer_id == user.id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    session.exec(delete(TeamMember).where(TeamMember.team_id == team.id))
    session.delete(team)
    session.commit()
    return {"message": f"Equipo '{team.name}' eliminado"}

# ------------------------------------------------
# Exportar equipo a PDF
# ------------------------------------------------
@router.get("/{team_id}/export", summary="Exporta un equipo en PDF con estadísticas y fichas de Pokémon")
def export_team_pdf(
    team_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logger.info(f"{user.username} exporta equipo {team_id} a PDF")

    team = session.exec(
        select(Team)
        .options(joinedload(Team.members).joinedload(TeamMember.pokedex_entry))
        .where(Team.id == team_id, Team.trainer_id == user.id)
    ).first()
    if not team:
        raise HTTPException(404, "Equipo no encontrado o no pertenece al usuario.")
    if not team.members:
        raise HTTPException(400, "El equipo no tiene Pokémon.")

    # --- GENERAR PDF  ---
    W, H = 1000, 1400
    page = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(page)
    try:
        FONT = ImageFont.truetype("arial.ttf", 22)
    except:
        FONT = ImageFont.load_default()
    draw.text((60, 40), f"Equipo: {team.name}", fill=(0, 0, 0), font=FONT)
    draw.text((60, 70), f"Descripción: {team.description or '-'}", fill=(50, 50, 50), font=FONT)
    draw.text((60, 110), f"Entrenador: {user.username}", fill=(0, 0, 0), font=FONT)
    draw.text((60, 140), f"Pokémon en el equipo: {len(team.members)}", fill=(0, 0, 0), font=FONT)

    offset_y = 180
    total_stats = []

    for m in team.members:
        entry = m.pokedex_entry
        if not entry:
            continue

        #  Compatibilidad con versión actual del servicio
        if hasattr(service, "get_pokemon_by_id"):
            data = service.get_pokemon_by_id(entry.pokemon_id)
        else:
            data = service.get_pokemon(entry.pokemon_id)
        stats = [s["base_stat"] for s in data.get("stats", [])]
        total_stats.append(sum(stats))

        name = data.get("name", "Desconocido").capitalize()
        draw.text((60, offset_y), f"{name}", fill=(0, 0, 0), font=FONT)
        level = getattr(entry, "level", "N/A")
        draw.text((260, offset_y), f"Nivel: {level}", fill=(0, 0, 0), font=FONT)
        draw.text((400, offset_y), f"Stats: {sum(stats)}", fill=(0, 0, 0), font=FONT)

        sprite_url = data.get("sprites", {}).get("front_default")
        if sprite_url:
            try:
                img_data = httpx.get(sprite_url, timeout=10).content
                sprite = Image.open(io.BytesIO(img_data)).convert("RGBA").resize((96, 96))
                page.paste(sprite, (750, offset_y - 30), sprite)
            except Exception as e:
                logger.warning(f"No se pudo cargar sprite: {e}")

        offset_y += 120

    avg_stats = round(statistics.mean(total_stats), 1) if total_stats else 0
    draw.text((60, offset_y + 20), f"Promedio de stats totales: {avg_stats}", fill=(0, 0, 0), font=FONT)

    out = io.BytesIO()
    page.save(out, format="PDF")
    out.seek(0)
    filename = f"team_{team.name}_{user.username}.pdf"

    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
