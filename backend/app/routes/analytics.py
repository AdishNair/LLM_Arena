import statistics

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Evaluation, ModelResponse
from app.schemas import LeaderboardRow, ThreadAnalytics

router = APIRouter(prefix='/analytics', tags=['analytics'])


def _overall_expr():
    return (Evaluation.relevance + Evaluation.coherence + Evaluation.factuality + Evaluation.usefulness + Evaluation.engagement) / 5.0


@router.get('/leaderboard', response_model=list[LeaderboardRow])
async def leaderboard(db: AsyncSession = Depends(get_db)) -> list[LeaderboardRow]:
    query = (
        select(
            ModelResponse.model_name.label('model_name'),
            func.avg(Evaluation.relevance).label('avg_relevance'),
            func.avg(Evaluation.coherence).label('avg_coherence'),
            func.avg(Evaluation.factuality).label('avg_factuality'),
            func.avg(Evaluation.usefulness).label('avg_usefulness'),
            func.avg(Evaluation.engagement).label('avg_engagement'),
            func.avg(_overall_expr()).label('avg_overall'),
            func.count(ModelResponse.id).label('total_responses'),
        )
        .join(Evaluation, Evaluation.response_id == ModelResponse.id)
        .group_by(ModelResponse.model_name)
        .order_by(func.avg(_overall_expr()).desc())
    )
    rows = (await db.execute(query)).all()

    return [
        LeaderboardRow(
            model_name=row.model_name,
            avg_relevance=float(row.avg_relevance),
            avg_coherence=float(row.avg_coherence),
            avg_factuality=float(row.avg_factuality),
            avg_usefulness=float(row.avg_usefulness),
            avg_engagement=float(row.avg_engagement),
            avg_overall=float(row.avg_overall),
            total_responses=int(row.total_responses),
        )
        for row in rows
    ]


@router.get('/thread/{thread_id}', response_model=ThreadAnalytics)
async def thread_analytics(thread_id: int, db: AsyncSession = Depends(get_db)) -> ThreadAnalytics:
    query = (
        select(
            ModelResponse.model_name.label('model_name'),
            func.avg(Evaluation.relevance).label('avg_relevance'),
            func.avg(Evaluation.coherence).label('avg_coherence'),
            func.avg(Evaluation.factuality).label('avg_factuality'),
            func.avg(Evaluation.usefulness).label('avg_usefulness'),
            func.avg(Evaluation.engagement).label('avg_engagement'),
            func.avg(_overall_expr()).label('avg_overall'),
            func.count(ModelResponse.id).label('total_responses'),
        )
        .join(Evaluation, Evaluation.response_id == ModelResponse.id)
        .where(ModelResponse.thread_id == thread_id)
        .group_by(ModelResponse.model_name)
    )
    rows = (await db.execute(query)).all()

    model_scores = [
        LeaderboardRow(
            model_name=row.model_name,
            avg_relevance=float(row.avg_relevance),
            avg_coherence=float(row.avg_coherence),
            avg_factuality=float(row.avg_factuality),
            avg_usefulness=float(row.avg_usefulness),
            avg_engagement=float(row.avg_engagement),
            avg_overall=float(row.avg_overall),
            total_responses=int(row.total_responses),
        )
        for row in rows
    ]

    overalls = [row.avg_overall for row in model_scores]
    agreement_index = float(max(0.0, 10.0 - statistics.pstdev(overalls))) if len(overalls) > 1 else 10.0
    response_count = sum(row.total_responses for row in model_scores)

    return ThreadAnalytics(
        thread_id=thread_id,
        response_count=response_count,
        model_scores=model_scores,
        agreement_index=round(agreement_index, 2),
    )
