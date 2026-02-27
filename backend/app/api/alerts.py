import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.deps import get_db, require_user_id
from ..models.alert import Alert, AlertMatch
from ..models.article import Article
from ..schemas.alert import AlertCreate, AlertMatchOut, AlertOut, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_to_out(alert: Alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        name=alert.name,
        keywords=json.loads(alert.keywords_json or "[]"),
        countries=json.loads(alert.countries_json or "[]"),
        active=alert.active,
        created_at=alert.created_at,
    )


# --- Static paths BEFORE /{id} ---


@router.get("/matches", response_model=list[AlertMatchOut])
async def list_matches(
    limit: int = Query(30, ge=1, le=200),
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            AlertMatch,
            Alert.name.label("alert_name"),
            Article.title.label("article_title"),
            Article.url.label("article_url"),
            Article.country.label("article_country"),
        )
        .join(Alert, AlertMatch.alert_id == Alert.id)
        .join(Article, AlertMatch.article_id == Article.id)
        .where(Alert.user_id == user_id)
        .order_by(AlertMatch.matched_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        AlertMatchOut(
            id=row[0].id,
            alert_id=row[0].alert_id,
            alert_name=row.alert_name,
            article_id=row[0].article_id,
            article_title=row.article_title,
            article_url=row.article_url,
            article_country=row.article_country,
            matched_at=row[0].matched_at,
            read=row[0].read,
        )
        for row in rows
    ]


@router.get("/unread-count")
async def unread_count(
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(func.count(AlertMatch.id))
        .join(Alert, AlertMatch.alert_id == Alert.id)
        .where(Alert.user_id == user_id, AlertMatch.read == False)  # noqa: E712
    )
    result = await db.execute(query)
    count = result.scalar() or 0
    return {"count": count}


@router.post("/mark-read")
async def mark_all_read(
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Get all alert IDs belonging to this user
    alert_ids_result = await db.execute(
        select(Alert.id).where(Alert.user_id == user_id)
    )
    alert_ids = [row[0] for row in alert_ids_result.all()]
    if alert_ids:
        await db.execute(
            update(AlertMatch)
            .where(AlertMatch.alert_id.in_(alert_ids), AlertMatch.read == False)  # noqa: E712
            .values(read=True)
        )
        await db.commit()
    return {"message": "Все отмечены как прочитанные"}


# --- CRUD (dynamic /{id} paths last) ---


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.user_id == user_id).order_by(Alert.created_at.desc())
    )
    return [_alert_to_out(a) for a in result.scalars().all()]


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    req: AlertCreate,
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    alert = Alert(
        user_id=user_id,
        name=req.name,
        keywords_json=json.dumps(req.keywords, ensure_ascii=False),
        countries_json=json.dumps(req.countries, ensure_ascii=False),
        active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _alert_to_out(alert)


@router.put("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: int,
    req: AlertUpdate,
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    if req.active is not None:
        alert.active = req.active
    if req.name is not None:
        alert.name = req.name
    if req.keywords is not None:
        alert.keywords_json = json.dumps(req.keywords, ensure_ascii=False)
    if req.countries is not None:
        alert.countries_json = json.dumps(req.countries, ensure_ascii=False)
    await db.commit()
    await db.refresh(alert)
    return _alert_to_out(alert)


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    user_id: int = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    await db.delete(alert)
    await db.commit()
    return {"message": f"Алерт '{alert.name}' удалён"}
