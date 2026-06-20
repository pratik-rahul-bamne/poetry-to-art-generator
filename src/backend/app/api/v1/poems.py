"""
Poem Routes — save, list, and delete user poems.
POST   /api/v1/poems
GET    /api/v1/poems
DELETE /api/v1/poems/{id}
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.poem_service import PoemService
from backend.app.schemas.poem import PoemCreateRequest, PoemResponse, PoemListResponse
from backend.app.api.v1.auth import get_current_user

router = APIRouter(prefix="/poems", tags=["Poems"])


@router.post("", response_model=PoemResponse, status_code=status.HTTP_201_CREATED)
def save_poem(
    payload: PoemCreateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Save a poem to the user's collection.
    Requires authentication.
    """
    service = PoemService(db)
    poem = service.save_poem(
        poem_text=payload.poem_text,
        user_id=user["sub"],
        title=payload.title,
        language=payload.language,
        theme=payload.theme,
        mood=payload.mood,
    )
    return PoemResponse(
        id=poem.id,
        title=poem.title,
        poem_text=poem.poem_text,
        language=poem.language,
        theme=poem.theme,
        mood=poem.mood,
        created_at=poem.created_at,
    )


@router.get("", response_model=PoemListResponse)
def list_poems(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the authenticated user's saved poems (paginated)."""
    service = PoemService(db)
    items, total = service.get_user_poems(user["sub"], page=page, per_page=per_page)
    return PoemListResponse(
        items=[
            PoemResponse(
                id=p.id, title=p.title, poem_text=p.poem_text,
                language=p.language, theme=p.theme, mood=p.mood,
                created_at=p.created_at,
            )
            for p in items
        ],
        total=total,
    )


@router.delete("/{poem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poem(
    poem_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a poem. Only the owner can delete their poem."""
    service = PoemService(db)
    success = service.delete_poem(poem_id, user["sub"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poem not found or you don't have permission to delete it.",
        )
