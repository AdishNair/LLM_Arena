from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ModelResponse, Rating, User
from app.schemas import ResponseRatingCreate
from app.services.dependencies import get_current_user

router = APIRouter(prefix='/responses', tags=['responses'])


@router.post('/rate')
async def rate_response(
    payload: ResponseRatingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    response = await db.get(ModelResponse, payload.response_id, options=[selectinload(ModelResponse.artifact)])
    if not response:
        raise HTTPException(status_code=404, detail='Response not found')
    if response.status != 'completed' or response.response_type == 'summary':
        raise HTTPException(status_code=400, detail='Only completed model responses can be rated')

    existing_q = await db.execute(
        select(Rating).where((Rating.response_id == payload.response_id) & (Rating.user_id == user.id))
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        existing.score = payload.score
    else:
        db.add(Rating(response_id=payload.response_id, user_id=user.id, score=payload.score))

    await db.commit()
    return {'status': 'ok'}
