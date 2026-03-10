import asyncio
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.conversation.conversation_manager import ConversationManager, Participant
from app.database import AsyncSessionLocal
from app.evaluation.evaluation_engine import EvaluationEngine
from app.models import Evaluation, EvaluationDetail, ModelResponse, ResponseArtifact, Thread

logger = logging.getLogger(__name__)


def _default_participants() -> list[dict[str, str]]:
    return [
        {'model_name': 'groq:llama-3.1-8b-instant', 'role': 'General analyst'},
        {'model_name': 'mistral:mistral-small-latest', 'role': 'Counterpoint reviewer'},
    ]


async def process_thread_async(thread_id: int, selected_models: list[str] | None = None, allow_model_replies: bool | None = None) -> None:
    async with AsyncSessionLocal() as db:
        thread_q = await db.execute(select(Thread).where(Thread.id == thread_id).options(selectinload(Thread.config)))
        thread = thread_q.scalar_one_or_none()
        if not thread:
            logger.error('Thread %s not found', thread_id)
            return

        participant_defs = thread.participants or _default_participants()
        if selected_models:
            participant_defs = [{'model_name': model_name, 'role': 'General analyst'} for model_name in selected_models]

        participants = [
            Participant(model_name=item['model_name'], role_name=item.get('role', 'General analyst'))
            for item in participant_defs
            if item.get('model_name')
        ]
        if not participants:
            logger.error('Thread %s has no valid participants configured', thread_id)
            return

        manager = ConversationManager(max_rounds=thread.conversation_rounds)
        generated = await manager.run(
            prompt=thread.prompt,
            participants=participants,
            allow_model_replies=thread.allow_model_replies if allow_model_replies is None else allow_model_replies,
            conversation_rounds=thread.conversation_rounds,
            include_summary=thread.include_summary,
        )

        last_response_id_by_model: dict[str, int] = {}
        previous_successful_text_by_model: dict[str, str] = {}
        stored: list[tuple[ModelResponse, ResponseArtifact]] = []

        for item in generated:
            parent_id = last_response_id_by_model.get(item.model_name) if item.response_type != 'summary' else None
            record = ModelResponse(
                thread_id=thread.id,
                model_name=item.model_name,
                response_text=item.response_text if item.status == 'completed' else '',
                parent_response_id=parent_id,
                round_number=item.round_number,
            )
            db.add(record)
            await db.flush()

            artifact = ResponseArtifact(
                response_id=record.id,
                role_name=item.role_name,
                status=item.status,
                error_detail=item.error_detail,
                response_type=item.response_type,
            )
            db.add(artifact)

            if item.response_type != 'summary':
                last_response_id_by_model[item.model_name] = record.id
            stored.append((record, artifact))

        evaluator = EvaluationEngine()
        for response, artifact in stored:
            if artifact.status != 'completed' or not response.response_text.strip():
                continue

            scores = await evaluator.evaluate(
                model_name=response.model_name,
                prompt=thread.prompt,
                response_text=response.response_text,
                role_name=artifact.role_name,
                previous_response_text=previous_successful_text_by_model.get(response.model_name),
                response_type=artifact.response_type,
            )

            evaluation = Evaluation(
                response_id=response.id,
                relevance=scores.relevance,
                coherence=scores.coherence,
                factuality=scores.factuality,
                usefulness=scores.usefulness,
                engagement=scores.engagement,
                notes=scores.notes,
            )
            db.add(evaluation)
            await db.flush()

            db.add(
                EvaluationDetail(
                    evaluation_id=evaluation.id,
                    overall_score=scores.overall_score,
                    role_adherence=scores.role_adherence,
                    debate_quality=scores.debate_quality,
                    evidence_quality=scores.evidence_quality,
                    improvement_score=scores.improvement_score,
                    evaluation_mode=scores.evaluation_mode,
                    judge_provider=scores.judge_provider,
                    judge_model=scores.judge_model,
                    failure_tags_json=json.dumps(scores.failure_tags),
                )
            )
            previous_successful_text_by_model[response.model_name] = response.response_text

        await db.commit()


@celery_app.task(name='process_thread')
def process_thread(
    thread_id: int,
    selected_models: list[str] | None = None,
    allow_model_replies: bool | None = None,
) -> None:
    asyncio.run(process_thread_async(thread_id, selected_models, allow_model_replies))
