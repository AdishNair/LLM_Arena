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


class ThreadCreate(BaseModel):
    title: str
    prompt: str
    subforum_id: int | None = None
    selected_models: list[str] = Field(default_factory=lambda: ['groq:llama-3.1-8b-instant', 'mistral:mistral-small-latest'])
    allow_model_replies: bool = True


class ThreadRerunRequest(BaseModel):
    selected_models: list[str] | None = None
    allow_model_replies: bool = True


class ThreadRead(BaseModel):
    id: int
    title: str
    prompt: str
    user_id: int
    subforum_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRead(BaseModel):
    id: int
    relevance: float
    coherence: float
    factuality: float
    usefulness: float
    engagement: float
    notes: str

    model_config = ConfigDict(from_attributes=True)


class ModelResponseRead(BaseModel):
    id: int
    thread_id: int
    model_name: str
    response_text: str
    parent_response_id: int | None
    round_number: int
    created_at: datetime
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
    total_responses: int


class ThreadAnalytics(BaseModel):
    thread_id: int
    response_count: int
    model_scores: list[LeaderboardRow]
    agreement_index: float


class EvaluationResult(BaseModel):
    model: str
    relevance: float
    coherence: float
    factuality: float
    usefulness: float
    engagement: float
    notes: str = ''
