from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SubforumCreate(BaseModel):
    name: str
    description: str = ''


class SubforumRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadParticipant(BaseModel):
    model_name: str
    role: str = Field(default='General analyst', max_length=255)


class ThreadCreate(BaseModel):
    title: str
    prompt: str
    subforum_id: int | None = None
    selected_models: list[str] = Field(default_factory=lambda: ['groq:llama-3.1-8b-instant', 'mistral:mistral-small-latest'])
    participants: list[ThreadParticipant] = Field(default_factory=list)
    allow_model_replies: bool = True
    conversation_rounds: int = Field(default=4, ge=1, le=8)
    include_summary: bool = True


class ThreadRerunRequest(BaseModel):
    selected_models: list[str] | None = None
    participants: list[ThreadParticipant] | None = None
    allow_model_replies: bool | None = None
    conversation_rounds: int | None = Field(default=None, ge=1, le=8)
    include_summary: bool | None = None


class ThreadRead(BaseModel):
    id: int
    title: str
    prompt: str
    user_id: int
    subforum_id: int | None
    created_at: datetime
    allow_model_replies: bool
    conversation_rounds: int
    include_summary: bool
    participants: list[ThreadParticipant] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EvaluationDetailRead(BaseModel):
    overall_score: float
    role_adherence: float
    debate_quality: float
    evidence_quality: float
    improvement_score: float
    evaluation_mode: str
    judge_provider: str
    judge_model: str
    failure_tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EvaluationRead(BaseModel):
    id: int
    relevance: float
    coherence: float
    factuality: float
    usefulness: float
    engagement: float
    notes: str
    detail: EvaluationDetailRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ModelResponseRead(BaseModel):
    id: int
    thread_id: int
    model_name: str
    response_text: str
    parent_response_id: int | None
    round_number: int
    created_at: datetime
    role_name: str = ''
    status: str = 'completed'
    error_detail: str = ''
    response_type: str = 'discussion'
    average_user_rating: float | None = None
    evaluations: list[EvaluationRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ThreadDetail(BaseModel):
    thread: ThreadRead
    responses: list[ModelResponseRead]


class ResponseRatingCreate(BaseModel):
    response_id: int
    score: int = Field(ge=1, le=5)


class LeaderboardRow(BaseModel):
    model_name: str
    avg_relevance: float
    avg_coherence: float
    avg_factuality: float
    avg_usefulness: float
    avg_engagement: float
    avg_overall: float
    blended_score: float
    avg_role_adherence: float
    avg_debate_quality: float
    avg_evidence_quality: float
    avg_improvement_score: float
    avg_human_rating: float | None = None
    total_responses: int
    successful_responses: int
    failed_responses: int


class ThreadAnalytics(BaseModel):
    thread_id: int
    response_count: int
    successful_response_count: int
    failed_response_count: int
    max_round_reached: int
    model_scores: list[LeaderboardRow]
    agreement_index: float
    thread_summary: str


class EvaluationResult(BaseModel):
    model: str
    relevance: float
    coherence: float
    factuality: float
    usefulness: float
    engagement: float
    overall_score: float
    role_adherence: float
    debate_quality: float
    evidence_quality: float
    improvement_score: float
    failure_tags: list[str] = Field(default_factory=list)
    evaluation_mode: str = 'judge'
    judge_provider: str = ''
    judge_model: str = ''
    notes: str = ''
