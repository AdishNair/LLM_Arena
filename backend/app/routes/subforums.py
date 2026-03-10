from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Subforum
from app.schemas import SubforumCreate, SubforumRead

router = APIRouter(prefix='/subforums', tags=['subforums'])


@router.post('', response_model=SubforumRead)
async def create_subforum(payload: SubforumCreate, db: AsyncSession = Depends(get_db)) -> Subforum:
    subforum = Subforum(name=payload.name, description=payload.description)
    db.add(subforum)
    await db.commit()
    await db.refresh(subforum)
    return subforum


@router.get('', response_model=list[SubforumRead])
async def list_subforums(db: AsyncSession = Depends(get_db)) -> list[Subforum]:
    result = await db.execute(select(Subforum).order_by(desc(Subforum.created_at)))
    return list(result.scalars().all())
