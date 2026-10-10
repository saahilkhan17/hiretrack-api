"""CRUD for job applications: list (filter/search/paginate), create, read,
update, delete, plus a per-status summary. Every route is scoped to the
authenticated user — users can only touch their own rows."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=schemas.PaginatedApplications)
def list_applications(
    status_filter: models.AppStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.JobApplication).filter(
        models.JobApplication.owner_id == user.id
    )
    if status_filter is not None:
        q = q.filter(models.JobApplication.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.JobApplication.company.ilike(like)
            | models.JobApplication.role.ilike(like)
        )
    total = q.count()
    items = (
        q.order_by(models.JobApplication.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.PaginatedApplications(
        total=total, page=page, page_size=page_size, items=items
    )


@router.post("", response_model=schemas.ApplicationOut, status_code=201)
def create_application(
    payload: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    app = models.JobApplication(**payload.model_dump(), owner_id=user.id)
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def _get_owned(app_id: int, user: models.User, db: Session) -> models.JobApplication:
    app = (
        db.query(models.JobApplication)
        .filter(
            models.JobApplication.id == app_id,
            models.JobApplication.owner_id == user.id,
        )
        .first()
    )
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.get("/stats/summary", response_model=list[schemas.StatusSummary])
def status_summary(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.JobApplication.status, func.count(models.JobApplication.id))
        .filter(models.JobApplication.owner_id == user.id)
        .group_by(models.JobApplication.status)
        .all()
    )
    return [schemas.StatusSummary(status=s, count=c) for s, c in rows]


@router.get("/{app_id}", response_model=schemas.ApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return _get_owned(app_id, user, db)


@router.patch("/{app_id}", response_model=schemas.ApplicationOut)
def update_application(
    app_id: int,
    payload: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    app = _get_owned(app_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    app = _get_owned(app_id, user, db)
    db.delete(app)
    db.commit()
    return None
