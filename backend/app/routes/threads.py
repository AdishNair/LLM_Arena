import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Evaluation, ModelResponse, Thread, ThreadConfig, User
from app.schemas import ThreadCreate, ThreadDetail, ThreadParticipant, ThreadRead, ThreadRerunRequest
from app.services.dependencies import get_current_user
from app.tasks import process_thread, process_thread_async

router = APIRouter(prefix='/threads', tags=['threads'])
settings = get_settings()
logger = logging.getLogger(__name__)


def _default_participants() -> list[ThreadParticipant]:
    return [
        ThreadParticipant(model_name='groq:llama-3.1-8b-instant', role='General analyst'),
        ThreadParticipant(model_name='mistral:mistral-small-latest', role='Counterpoint reviewer'),
    ]


def _normalize_participants(
    selected_models: list[str] | None,
    participants: list[ThreadParticipant] | None,
) -> list[ThreadParticipant]:
    if participants:
        normalized: list[ThreadParticipant] = []
        seen: set[str] = set()
        for participant in participants:
            model_name = participant.model_name.strip()
            if not model_name or model_name in seen:
                continue
            seen.add(model_name)
            normalized.append(
                ThreadParticipant(
                    model_name=model_name,
                    role=participant.role.strip() or 'General analyst',
                )
            )
        if normalized:
            return normalized

    if selected_models:
        return [
            ThreadParticipant(model_name=model_name, role='General analyst')
            for model_name in dict.fromkeys(model_name.strip() for model_name in selected_models if model_name.strip())
        ]

    return _default_participants()


def _serialize_participants(participants: list[ThreadParticipant]) -> str:
    return json.dumps([participant.model_dump() for participant in participants])


def _kickoff_generation(thread_id: int) -> None:
    if settings.use_celery:
        try:
            process_thread.delay(thread_id)
            return
        except Exception as exc:
            logger.exception('Celery enqueue failed, falling back to in-process execution: %s', exc)

    asyncio.create_task(process_thread_async(thread_id))


async def _load_thread(db: AsyncSession, thread_id: int) -> Thread | None:
    result = await db.execute(select(Thread).where(Thread.id == thread_id).options(selectinload(Thread.config)))
    return result.scalar_one_or_none()


@router.post('/create', response_model=ThreadRead)
async def create_thread(
    payload: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Thread:
    participants = _normalize_participants(payload.selected_models, payload.participants)

    thread = Thread(
        title=payload.title,
        prompt=payload.prompt,
        user_id=user.id,
        subforum_id=payload.subforum_id,
    )
    db.add(thread)
    await db.flush()

    db.add(
        ThreadConfig(
            thread_id=thread.id,
            allow_model_replies=payload.allow_model_replies,
            conversation_rounds=payload.conversation_rounds,
            include_summary=payload.include_summary,
            participants_json=_serialize_participants(participants),
        )
    )
    await db.commit()

    thread = await _load_thread(db, thread.id)
    if not thread:
        raise HTTPException(status_code=500, detail='Thread creation failed')

    _kickoff_generation(thread.id)
    return thread


@router.post('/{thread_id}/rerun', response_model=ThreadRead)
async def rerun_thread(
    thread_id: int,
    payload: ThreadRerunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Thread:
    thread = await _load_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail='Thread not found')
    if thread.user_id != user.id:
        raise HTTPException(status_code=403, detail='Not allowed to rerun this thread')

    participants = _normalize_participants(
        payload.selected_models if payload else None,
        payload.participants if payload else None,
    )
    if not payload or (not payload.selected_models and not payload.participants):
        participants = [ThreadParticipant(**item) for item in (thread.participants or [participant.model_dump() for participant in _default_participants()])]

    config = thread.config or ThreadConfig(thread_id=thread.id, participants_json='[]')
    config.allow_model_replies = payload.allow_model_replies if payload and payload.allow_model_replies is not None else thread.allow_model_replies
    config.conversation_rounds = payload.conversation_rounds if payload and payload.conversation_rounds is not None else thread.conversation_rounds
    config.include_summary = payload.include_summary if payload and payload.include_summary is not None else thread.include_summary
    config.participants_json = _serialize_participants(participants)
    db.add(config)

    await db.execute(delete(ModelResponse).where(ModelResponse.thread_id == thread_id))
    await db.commit()

    thread = await _load_thread(db, thread.id)
    if not thread:
        raise HTTPException(status_code=500, detail='Thread rerun failed')

    _kickoff_generation(thread.id)
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
    result = await db.execute(select(Thread).options(selectinload(Thread.config)).order_by(desc(Thread.created_at)).limit(100))
    return list(result.scalars().all())


@router.get('/{thread_id}', response_model=ThreadDetail)
async def get_thread(thread_id: int, db: AsyncSession = Depends(get_db)) -> ThreadDetail:
    thread = await _load_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail='Thread not found')

    responses_query = await db.execute(
        select(ModelResponse)
        .where(ModelResponse.thread_id == thread_id)
        .options(
            selectinload(ModelResponse.artifact),
            selectinload(ModelResponse.ratings),
            selectinload(ModelResponse.evaluations).selectinload(Evaluation.detail),
        )
        .order_by(ModelResponse.round_number.asc(), ModelResponse.created_at.asc())
    )

    responses = list(responses_query.scalars().all())
    return ThreadDetail(thread=thread, responses=responses)
