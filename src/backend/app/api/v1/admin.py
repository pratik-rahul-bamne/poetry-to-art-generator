"""
Admin Routes — dashboard stats, user management, AI usage monitoring.
All endpoints require admin role.

GET  /api/v1/admin/stats
GET  /api/v1/admin/users
GET  /api/v1/admin/logs
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.repositories.user_repo import UserRepository
from backend.app.repositories.generation_repo import GenerationRepository
from backend.app.repositories.poem_repo import PoemRepository
from backend.app.models.activity_log import ActivityLog
from backend.app.schemas.user import AdminStatsResponse, AdminUserListResponse, UserResponse
from backend.app.api.v1.auth import get_admin_user
from backend.app.core.logger import get_logger

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = get_logger("api")


@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    """
    System-wide statistics for the admin dashboard.
    Returns user counts, poem counts, generation counts, and provider breakdown.
    """
    user_repo = UserRepository(db)
    poem_repo = PoemRepository(db)
    gen_repo  = GenerationRepository(db)

    return AdminStatsResponse(
        total_users=user_repo.list_all()[1],
        active_users=user_repo.count_active(),
        total_poems=poem_repo.count_all(),
        total_generations=gen_repo.count_all(),
        total_downloads=gen_repo.count_downloads(),
        provider_breakdown=gen_repo.count_by_provider(),
    )


@router.get("/users", response_model=AdminUserListResponse)
def admin_list_users(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    """List all registered users (paginated)."""
    repo = UserRepository(db)
    skip = (page - 1) * per_page
    users, total = repo.list_all(skip=skip, limit=per_page)
    return AdminUserListResponse(
        items=[
            UserResponse(
                id=u.id, name=u.name, email=u.email,
                role=u.role, status=u.status,
                created_at=u.created_at, last_login=u.last_login,
            )
            for u in users
        ],
        total=total,
    )


@router.get("/logs")
def admin_activity_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    """Return the most recent activity log entries."""
    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "module": log.module,
            "description": log.description,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
