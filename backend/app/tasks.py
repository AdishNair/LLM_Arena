import asyncio
import logging

from app.celery_app import celery_app
from app.conversation.conversation_manager import ConversationManager
from app.database import AsyncSessionLocal
from app.evaluation.evaluation_engine import EvaluationEngine
from app.models import Evaluation, ModelResponse, Thread

logger = logging.getLogger(__name__)


async def process_thread_async(thread_id: int, selected_models: list[str], allow_model_replies: bool) -> None:
    async with AsyncSessionLocal() as db:
        thread = await db.get(Thread, thread_id)
        if not thread:
            logger.error('Thread %s not found', thread_id)
            return

        manager = ConversationManager()
        generated = await manager.run(
            prompt=thread.prompt,
            selected_models=selected_models,
            allow_model_replies=allow_model_replies,
        )

        round_one_map: dict[str, int] = {}
        stored: list[ModelResponse] = []

        for item in generated:
            parent_id = None
            if item.round_number == 2 and item.parent_model_name:
                parent_id = round_one_map.get(item.parent_model_name)

            record = ModelResponse(
                thread_id=thread.id,
                model_name=item.model_name,
                response_text=item.response_text,
                parent_response_id=parent_id,
                round_number=item.round_number,
            )
            db.add(record)
            await db.flush()

            if item.round_number == 1:
                round_one_map[item.model_name] = record.id
            stored.append(record)

        evaluator = EvaluationEngine()
        for response in stored:
            scores = await evaluator.evaluate(
                model_name=response.model_name,
                prompt=thread.prompt,
                response_text=response.response_text,
            )
            db.add(
                Evaluation(
                    response_id=response.id,
                    relevance=scores.relevance,
                    coherence=scores.coherence,
                    factuality=scores.factuality,
                    usefulness=scores.usefulness,
                    engagement=scores.engagement,
                    notes=scores.notes,
                )
            )

        await db.commit()


@celery_app.task(name='process_thread')
def process_thread(thread_id: int, selected_models: list[str], allow_model_replies: bool = True) -> None:
    asyncio.run(process_thread_async(thread_id, selected_models, allow_model_replies))
