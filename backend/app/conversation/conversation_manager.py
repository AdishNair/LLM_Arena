from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.llm_clients.registry import get_client, split_model_identifier

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class Participant:
    model_name: str
    role_name: str


@dataclass
class GeneratedResponse:
    model_name: str
    role_name: str
    response_text: str
    parent_model_name: str | None
    round_number: int
    status: str = 'completed'
    error_detail: str = ''
    response_type: str = 'discussion'


class ConversationManager:
    def __init__(self, max_rounds: int | None = None):
        self.max_rounds = max_rounds or settings.max_conversation_rounds

    async def run(
        self,
        prompt: str,
        participants: list[Participant],
        allow_model_replies: bool = True,
        conversation_rounds: int | None = None,
        include_summary: bool = True,
    ) -> list[GeneratedResponse]:
        if not participants:
            return []

        total_rounds = max(1, min(conversation_rounds or self.max_rounds, 8))
        responses: list[GeneratedResponse] = []
        histories: dict[str, list[GeneratedResponse]] = {participant.model_name: [] for participant in participants}

        current_round = await self._generate_initial_round(prompt, participants)
        responses.extend(current_round)
        self._store_successes(histories, current_round)

        for round_number in range(2, total_rounds + 1):
            current_round = await self._generate_followup_round(
                prompt=prompt,
                participants=participants,
                histories=histories,
                previous_round=current_round,
                round_number=round_number,
                allow_model_replies=allow_model_replies,
            )
            responses.extend(current_round)
            self._store_successes(histories, current_round)

        if include_summary and responses:
            summary = await self._summarize_discussion(prompt, participants, responses)
            if summary:
                responses.append(summary)

        return responses

    async def _generate_initial_round(self, prompt: str, participants: list[Participant]) -> list[GeneratedResponse]:
        tasks = [
            (
                participant,
                1,
                'initial',
                None,
                asyncio.create_task(
                    self._call_model(
                        model_id=participant.model_name,
                        role_name=participant.role_name,
                        prompt=self._build_initial_prompt(prompt, participant),
                        context=self._build_context(participant.role_name),
                        parent_model_name=None,
                        round_number=1,
                        response_type='initial',
                    )
                ),
            )
            for participant in participants
        ]
        return await self._collect_tasks(tasks)

    async def _generate_followup_round(
        self,
        prompt: str,
        participants: list[Participant],
        histories: dict[str, list[GeneratedResponse]],
        previous_round: list[GeneratedResponse],
        round_number: int,
        allow_model_replies: bool,
    ) -> list[GeneratedResponse]:
        tasks = []
        for participant in participants:
            task = asyncio.create_task(
                self._call_model(
                    model_id=participant.model_name,
                    role_name=participant.role_name,
                    prompt=self._build_followup_prompt(
                        prompt=prompt,
                        participant=participant,
                        histories=histories,
                        previous_round=previous_round,
                        round_number=round_number,
                        allow_model_replies=allow_model_replies,
                    ),
                    context=self._build_context(participant.role_name),
                    parent_model_name=participant.model_name,
                    round_number=round_number,
                    response_type='followup',
                )
            )
            tasks.append((participant, round_number, 'followup', participant.model_name, task))
        return await self._collect_tasks(tasks)

    async def _summarize_discussion(
        self,
        prompt: str,
        participants: list[Participant],
        responses: list[GeneratedResponse],
    ) -> GeneratedResponse | None:
        model_id = 'groq:llama-3.1-8b-instant'
        participant_summary = '\n'.join([f'- {participant.model_name}: {participant.role_name}' for participant in participants])
        discussion = '\n\n'.join(
            [
                f'Round {response.round_number} | {response.model_name} | {response.role_name} | {response.status}\n'
                f'{response.response_text or response.error_detail}'
                for response in responses
                if response.response_type != 'summary'
            ]
        )
        summary_prompt = (
            f'User prompt:\n{prompt}\n\n'
            f'Participants:\n{participant_summary}\n\n'
            f'Discussion transcript:\n{discussion}\n\n'
            'Write a synthesis that highlights the best contributions, unresolved disagreements, and a pragmatic final answer.'
        )
        try:
            return await self._call_model(
                model_id=model_id,
                role_name='Synthesis moderator',
                prompt=summary_prompt,
                context=[{'role': 'system', 'content': 'You synthesize multi-model deliberations into a clear summary.'}],
                parent_model_name=None,
                round_number=max((response.round_number for response in responses), default=0) + 1,
                response_type='summary',
            )
        except Exception as exc:
            logger.warning('Summary model failed: %s', exc)
            return GeneratedResponse(
                model_name=model_id,
                role_name='Synthesis moderator',
                response_text='',
                parent_model_name=None,
                round_number=max((response.round_number for response in responses), default=0) + 1,
                status='failed',
                error_detail=f'Summary unavailable: {type(exc).__name__}: {exc}',
                response_type='summary',
            )

    async def _collect_tasks(
        self,
        tasks: list[tuple[Participant, int, str, str | None, asyncio.Task[GeneratedResponse]]],
    ) -> list[GeneratedResponse]:
        outputs: list[GeneratedResponse] = []
        for participant, round_number, response_type, parent_model_name, task in tasks:
            try:
                outputs.append(await task)
            except Exception as exc:
                logger.exception('Model call failed for %s: %s', participant.model_name, exc)
                outputs.append(
                    GeneratedResponse(
                        model_name=participant.model_name,
                        role_name=participant.role_name,
                        response_text='',
                        parent_model_name=parent_model_name,
                        round_number=round_number,
                        status='failed',
                        error_detail=f'{type(exc).__name__}: {exc}',
                        response_type=response_type,
                    )
                )
        return outputs

    def _store_successes(
        self,
        histories: dict[str, list[GeneratedResponse]],
        responses: list[GeneratedResponse],
    ) -> None:
        for response in responses:
            if response.status == 'completed':
                histories.setdefault(response.model_name, []).append(response)

    def _build_context(self, role_name: str) -> list[dict[str, str]]:
        return [
            {
                'role': 'system',
                'content': (
                    'You are participating in a structured multi-model evaluation. '
                    'Stay faithful to your assigned role, be explicit about uncertainty, and avoid filler.'
                ),
            },
            {'role': 'system', 'content': f'Assigned role: {role_name}'},
        ]

    def _build_initial_prompt(self, prompt: str, participant: Participant) -> str:
        return (
            f'User prompt:\n{prompt}\n\n'
            f'Your assigned role:\n{participant.role_name}\n\n'
            'Produce your first response from that role. Be concrete, answer the task directly, and note uncertainty where needed.'
        )

    def _build_followup_prompt(
        self,
        prompt: str,
        participant: Participant,
        histories: dict[str, list[GeneratedResponse]],
        previous_round: list[GeneratedResponse],
        round_number: int,
        allow_model_replies: bool,
    ) -> str:
        own_history = histories.get(participant.model_name, [])
        own_previous = own_history[-1].response_text if own_history else 'No prior answer.'

        peer_updates = [
            f'{response.model_name} ({response.role_name}): {response.response_text}'
            for response in previous_round
            if response.status == 'completed' and response.model_name != participant.model_name
        ]
        peer_block = '\n\n'.join(peer_updates) if peer_updates else 'No peer updates available.'

        if allow_model_replies:
            return (
                f'User prompt:\n{prompt}\n\n'
                f'Your assigned role:\n{participant.role_name}\n\n'
                f'Your previous answer:\n{own_previous}\n\n'
                f'Peer updates from round {round_number - 1}:\n{peer_block}\n\n'
                'Write your next response from your role. Refine your own answer, challenge weak points, add missing evidence, '
                'or converge where another model is correct.'
            )

        return (
            f'User prompt:\n{prompt}\n\n'
            f'Your assigned role:\n{participant.role_name}\n\n'
            f'Your previous answer:\n{own_previous}\n\n'
            'Write a stronger revision of your answer from the same role. Improve specificity, structure, and evidence-awareness.'
        )

    async def _call_model(
        self,
        model_id: str,
        role_name: str,
        prompt: str,
        context: list[dict] | None,
        parent_model_name: str | None,
        round_number: int,
        response_type: str,
    ) -> GeneratedResponse:
        provider, model = split_model_identifier(model_id)
        client = get_client(provider)
        response_text = await client.generate_response(model=model, prompt=prompt, context=context)
        return GeneratedResponse(
            model_name=model_id,
            role_name=role_name,
            response_text=response_text,
            parent_model_name=parent_model_name,
            round_number=round_number,
            response_type=response_type,
        )
