import statistics
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Evaluation, ModelResponse
from app.schemas import LeaderboardRow, ThreadAnalytics

router = APIRouter(prefix='/analytics', tags=['analytics'])


def _judge_overall(evaluation: Evaluation) -> float:
    if evaluation.detail:
        return float(evaluation.detail.overall_score)
    base = (
        evaluation.relevance
        + evaluation.coherence
        + evaluation.factuality
        + evaluation.usefulness
        + evaluation.engagement
    ) / 5.0
    return float(round(base, 2))


def _safe_mean(values: list[float]) -> float:
    return round(float(sum(values) / len(values)), 2) if values else 0.0


def _human_rating_to_ten_scale(response: ModelResponse) -> float | None:
    if response.average_user_rating is None:
        return None
    return round(response.average_user_rating * 2, 2)


def _blended_score(judge_score: float, human_score: float | None) -> float:
    if human_score is None:
        return round(judge_score, 2)
    return round((judge_score * 0.7) + (human_score * 0.3), 2)


def _is_countable(response: ModelResponse) -> bool:
    return response.response_type != 'summary'


def _is_success(response: ModelResponse) -> bool:
    return response.status == 'completed' and _is_countable(response)


def _build_row(model_name: str, responses: list[ModelResponse]) -> LeaderboardRow:
    countable = [response for response in responses if _is_countable(response)]
    successful = [response for response in countable if _is_success(response)]
    failed = [response for response in countable if response.status != 'completed']

    evaluations = [response.evaluations[0] for response in successful if response.evaluations]
    judge_scores = [_judge_overall(evaluation) for evaluation in evaluations]
    human_scores = [_human_rating_to_ten_scale(response) for response in successful]
    blended_scores = [
        _blended_score(_judge_overall(response.evaluations[0]), _human_rating_to_ten_scale(response))
        for response in successful
        if response.evaluations
    ]

    role_adherence = [
        evaluation.detail.role_adherence
        for evaluation in evaluations
        if evaluation.detail
    ]
    debate_quality = [
        evaluation.detail.debate_quality
        for evaluation in evaluations
        if evaluation.detail
    ]
    evidence_quality = [
        evaluation.detail.evidence_quality
        for evaluation in evaluations
        if evaluation.detail
    ]
    improvement_scores = [
        evaluation.detail.improvement_score
        for evaluation in evaluations
        if evaluation.detail
    ]
    human_values = [score for score in human_scores if score is not None]

    return LeaderboardRow(
        model_name=model_name,
        avg_relevance=_safe_mean([evaluation.relevance for evaluation in evaluations]),
        avg_coherence=_safe_mean([evaluation.coherence for evaluation in evaluations]),
        avg_factuality=_safe_mean([evaluation.factuality for evaluation in evaluations]),
        avg_usefulness=_safe_mean([evaluation.usefulness for evaluation in evaluations]),
        avg_engagement=_safe_mean([evaluation.engagement for evaluation in evaluations]),
        avg_overall=_safe_mean(judge_scores),
        blended_score=_safe_mean(blended_scores),
        avg_role_adherence=_safe_mean(role_adherence),
        avg_debate_quality=_safe_mean(debate_quality),
        avg_evidence_quality=_safe_mean(evidence_quality),
        avg_improvement_score=_safe_mean(improvement_scores),
        avg_human_rating=_safe_mean(human_values) if human_values else None,
        total_responses=len(countable),
        successful_responses=len(successful),
        failed_responses=len(failed),
    )


async def _load_responses(db: AsyncSession, thread_id: int | None = None) -> list[ModelResponse]:
    query = (
        select(ModelResponse)
        .options(
            selectinload(ModelResponse.artifact),
            selectinload(ModelResponse.ratings),
            selectinload(ModelResponse.evaluations).selectinload(Evaluation.detail),
        )
        .order_by(ModelResponse.created_at.asc())
    )
    if thread_id is not None:
        query = query.where(ModelResponse.thread_id == thread_id)
    rows = await db.execute(query)
    return list(rows.scalars().all())


def _group_rows(responses: list[ModelResponse]) -> list[LeaderboardRow]:
    grouped: dict[str, list[ModelResponse]] = defaultdict(list)
    for response in responses:
        if response.response_type == 'summary':
            continue
        grouped[response.model_name].append(response)
    rows = [_build_row(model_name, model_responses) for model_name, model_responses in grouped.items()]
    return sorted(rows, key=lambda row: row.blended_score, reverse=True)


@router.get('/leaderboard', response_model=list[LeaderboardRow])
async def leaderboard(db: AsyncSession = Depends(get_db)) -> list[LeaderboardRow]:
    responses = await _load_responses(db)
    return _group_rows(responses)


@router.get('/thread/{thread_id}', response_model=ThreadAnalytics)
async def thread_analytics(thread_id: int, db: AsyncSession = Depends(get_db)) -> ThreadAnalytics:
    responses = await _load_responses(db, thread_id=thread_id)
    model_scores = _group_rows(responses)

    blended_scores = [row.blended_score for row in model_scores if row.successful_responses]
    agreement_index = float(max(0.0, 10.0 - statistics.pstdev(blended_scores))) if len(blended_scores) > 1 else 10.0
    successful_response_count = sum(row.successful_responses for row in model_scores)
    failed_response_count = sum(row.failed_responses for row in model_scores)
    response_count = successful_response_count + failed_response_count
    max_round_reached = max((response.round_number for response in responses if _is_countable(response)), default=0)

    if not model_scores:
        thread_summary = 'No successful responses are available yet.'
    else:
        best = model_scores[0]
        thread_summary = (
            f'Best blended score: {best.model_name} at {best.blended_score:.2f}. '
            f'Observed {successful_response_count} successful responses, {failed_response_count} failures, '
            f'and up to round {max_round_reached}.'
        )

    return ThreadAnalytics(
        thread_id=thread_id,
        response_count=response_count,
        successful_response_count=successful_response_count,
        failed_response_count=failed_response_count,
        max_round_reached=max_round_reached,
        model_scores=model_scores,
        agreement_index=round(agreement_index, 2),
        thread_summary=thread_summary,
    )
