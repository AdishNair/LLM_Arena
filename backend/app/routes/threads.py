import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import ModelResponse, Thread, User
from app.schemas import ThreadCreate, ThreadDetail, ThreadRead, ThreadRerunRequest
from app.services.dependencies import get_current_user
from app.tasks import process_thread, process_thread_async

router = APIRouter(prefix='/threads', tags=['threads'])
settings = get_settings()
logger = logging.getLogger(__name__)


def _kickoff_generation(thread_id: int, selected_models: list[str], allow_model_replies: bool) -> None:
    if settings.use_celery:
        try:
            process_thread.delay(thread_id, selected_models, allow_model_replies)
            return
        except Exception as exc:
            logger.exception('Celery enqueue failed, falling back to in-process execution: %s', exc)

    asyncio.create_task(process_thread_async(thread_id, selected_models, allow_model_replies))


@router.post('/create', response_model=ThreadRead)
async def create_thread(
    payload: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Thread:
    thread = Thread(
        title=payload.title,
        prompt=payload.prompt,
        user_id=user.id,
        subforum_id=payload.subforum_id,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)

    _kickoff_generation(thread.id, payload.selected_models, payload.allow_model_replies)
    return thread


@router.post('/{thread_id}/rerun', response_model=ThreadRead)
async def rerun_thread(
    thread_id: int,
    payload: ThreadRerunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Thread:
    thread = await db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail='Thread not found')
    if thread.user_id != user.id:
        raise HTTPException(status_code=403, detail='Not allowed to rerun this thread')

    if payload and payload.selected_models:
        selected_models = payload.selected_models
    else:
        existing_models_q = await db.execute(
            select(ModelResponse.model_name)
            .where((ModelResponse.thread_id == thread_id) & (ModelResponse.round_number == 1))
            .distinct()
        )
        selected_models = list(existing_models_q.scalars().all())
        if not selected_models:
            selected_models = ['groq:llama-3.1-8b-instant', 'mistral:mistral-small-latest']

    allow_model_replies = payload.allow_model_replies if payload else True

    await db.execute(delete(ModelResponse).where(ModelResponse.thread_id == thread_id))
    await db.commit()

    _kickoff_generation(thread.id, selected_models, allow_model_replies)
    return thread


@router.delete('/{thread_id}')
async def delete_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    thread = await db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail='Thread not found')
    if thread.user_id != user.id:
        raise HTTPException(status_code=403, detail='Not allowed to delete this thread')

    await db.delete(thread)
    await db.commit()
    return {'status': 'deleted', 'thread_id': thread_id}


@router.get('', response_model=list[ThreadRead])
async def list_threads(db: AsyncSession = Depends(get_db)) -> list[Thread]:
    result = await db.execute(select(Thread).order_by(desc(Thread.created_at)).limit(100))
    return list(result.scalars().all())


@router.get('/{thread_id}', response_model=ThreadDetail)
async def get_thread(thread_id: int, db: AsyncSession = Depends(get_db)) -> ThreadDetail:
    thread_query = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = thread_query.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail='Thread not found')

    responses_query = await db.execute(
        select(ModelResponse)
        .where(ModelResponse.thread_id == thread_id)
        .options(selectinload(ModelResponse.evaluations))
        .order_by(ModelResponse.round_number.asc(), ModelResponse.created_at.asc())
    )

    responses = list(responses_query.scalars().all())
    return ThreadDetail(thread=thread, responses=responses)
