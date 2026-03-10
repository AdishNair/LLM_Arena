from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.llm_clients.registry import get_client, split_model_identifier

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class GeneratedResponse:
    model_name: str
    response_text: str
    parent_model_name: str | None
    round_number: int


class ConversationManager:
    def __init__(self, max_rounds: int | None = None):
        self.max_rounds = max_rounds or settings.max_conversation_rounds

    async def run(
        self,
        prompt: str,
        selected_models: list[str],
        allow_model_replies: bool = True,
    ) -> list[GeneratedResponse]:
        responses: list[GeneratedResponse] = []

        round_one = await self._generate_round(prompt=prompt, model_ids=selected_models, round_number=1, context=[])
        responses.extend(round_one)

        if allow_model_replies and self.max_rounds >= 2 and round_one:
            round_two = await self._generate_cross_model_replies(prompt, selected_models, round_one)
            responses.extend(round_two)

        if self.max_rounds >= 3 and responses:
            summary = await self._summarize_discussion(prompt, responses)
            if summary:
                responses.append(summary)

        return responses

    async def _generate_round(
        self,
        prompt: str,
        model_ids: list[str],
        round_number: int,
        context: list[dict],
    ) -> list[GeneratedResponse]:
        tasks = [
            (model_id, asyncio.create_task(self._call_model(model_id, prompt, context, None, round_number)))
            for model_id in model_ids
        ]

        outputs: list[GeneratedResponse] = []
        for model_id, task in tasks:
            try:
                outputs.append(await task)
            except Exception as exc:
                logger.exception('Model call failed for %s: %s', model_id, exc)
                outputs.append(
                    GeneratedResponse(
                        model_name=model_id,
                        response_text=f'Error from {model_id}: {type(exc).__name__}: {exc}',
                        parent_model_name=None,
                        round_number=round_number,
                    )
                )
        return outputs

    async def _generate_cross_model_replies(
        self,
        original_prompt: str,
        selected_models: list[str],
        round_one: list[GeneratedResponse],
    ) -> list[GeneratedResponse]:
        tasks: list[tuple[str, str, asyncio.Task]] = []
        for model_id in selected_models:
            for target in round_one:
                if target.model_name == model_id:
                    continue
                reply_prompt = (
                    f"Original user prompt:\n{original_prompt}\n\n"
                    f"Another model ({target.model_name}) answered:\n{target.response_text}\n\n"
                    'Reply with either support, critique, or expansion in <= 160 words.'
                )
                context = [{'role': 'system', 'content': 'You are in a multi-model debate.'}]
                task = asyncio.create_task(self._call_model(model_id, reply_prompt, context, target.model_name, 2))
                tasks.append((model_id, target.model_name, task))

        outputs: list[GeneratedResponse] = []
        for model_id, target_model, task in tasks:
            try:
                outputs.append(await task)
            except Exception as exc:
                logger.exception('Round 2 model reply failed for %s: %s', model_id, exc)
                outputs.append(
                    GeneratedResponse(
                        model_name=model_id,
                        response_text=f'Error from {model_id}: {type(exc).__name__}: {exc}',
                        parent_model_name=target_model,
                        round_number=2,
                    )
                )
        return outputs

    async def _summarize_discussion(self, prompt: str, responses: list[GeneratedResponse]) -> GeneratedResponse | None:
        model_id = 'groq:llama-3.1-8b-instant'
        discussion = '\n\n'.join([f"{r.model_name} (r{r.round_number}): {r.response_text}" for r in responses])
        summary_prompt = (
            f'User prompt: {prompt}\n\nDiscussion:\n{discussion}\n\n'
            'Summarize key agreements/disagreements and best final answer in <= 220 words.'
        )
        try:
            return await self._call_model(model_id, summary_prompt, [], None, 3)
        except Exception as exc:
            logger.warning('Summary model failed: %s', exc)
            return GeneratedResponse(
                model_name=model_id,
                response_text=f'Summary unavailable: {type(exc).__name__}: {exc}',
                parent_model_name=None,
                round_number=3,
            )

    async def _call_model(
        self,
        model_id: str,
        prompt: str,
        context: list[dict] | None,
        parent_model_name: str | None,
        round_number: int,
    ) -> GeneratedResponse:
        provider, model = split_model_identifier(model_id)
        client = get_client(provider)

        response_text = await client.generate_response(model=model, prompt=prompt, context=context)
        return GeneratedResponse(
            model_name=model_id,
            response_text=response_text,
            parent_model_name=parent_model_name,
            round_number=round_number,
        )

