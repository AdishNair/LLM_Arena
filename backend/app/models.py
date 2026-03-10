from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threads: Mapped[list['Thread']] = relationship(back_populates='user')
    ratings: Mapped[list['Rating']] = relationship(back_populates='user')
    posts: Mapped[list['Post']] = relationship(back_populates='user')


class Subforum(Base):
    __tablename__ = 'subforums'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threads: Mapped[list['Thread']] = relationship(back_populates='subforum')


class Thread(Base):
    __tablename__ = 'threads'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    subforum_id: Mapped[int | None] = mapped_column(ForeignKey('subforums.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped['User'] = relationship(back_populates='threads')
    subforum: Mapped['Subforum'] = relationship(back_populates='threads')
    model_responses: Mapped[list['ModelResponse']] = relationship(back_populates='thread', cascade='all, delete-orphan')
    posts: Mapped[list['Post']] = relationship(back_populates='thread', cascade='all, delete-orphan')
    config: Mapped['ThreadConfig | None'] = relationship(back_populates='thread', uselist=False, cascade='all, delete-orphan')

    @property
    def allow_model_replies(self) -> bool:
        return self.config.allow_model_replies if self.config else True

    @property
    def conversation_rounds(self) -> int:
        return self.config.conversation_rounds if self.config else 3

    @property
    def include_summary(self) -> bool:
        return self.config.include_summary if self.config else True

    @property
    def participants(self) -> list[dict[str, str]]:
        return self.config.participants if self.config else []


class ThreadConfig(Base):
    __tablename__ = 'thread_configs'

    thread_id: Mapped[int] = mapped_column(ForeignKey('threads.id', ondelete='CASCADE'), primary_key=True)
    allow_model_replies: Mapped[bool] = mapped_column(Boolean, default=True)
    conversation_rounds: Mapped[int] = mapped_column(Integer, default=3)
    include_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    participants_json: Mapped[str] = mapped_column(Text, default='[]')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped['Thread'] = relationship(back_populates='config')

    @property
    def participants(self) -> list[dict[str, str]]:
        try:
            data = json.loads(self.participants_json or '[]')
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        participants: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            model_name = str(item.get('model_name', '')).strip()
            role = str(item.get('role', '')).strip()
            if model_name:
                participants.append({'model_name': model_name, 'role': role})
        return participants


class Post(Base):
    __tablename__ = 'posts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey('threads.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text)
    parent_post_id: Mapped[int | None] = mapped_column(ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped['Thread'] = relationship(back_populates='posts')
    user: Mapped['User'] = relationship(back_populates='posts')


class ModelResponse(Base):
    __tablename__ = 'model_responses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey('threads.id', ondelete='CASCADE'), index=True)
    model_name: Mapped[str] = mapped_column(String(100), index=True)
    response_text: Mapped[str] = mapped_column(Text)
    parent_response_id: Mapped[int | None] = mapped_column(ForeignKey('model_responses.id', ondelete='CASCADE'), nullable=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thread: Mapped['Thread'] = relationship(back_populates='model_responses')
    evaluations: Mapped[list['Evaluation']] = relationship(back_populates='response', cascade='all, delete-orphan')
    ratings: Mapped[list['Rating']] = relationship(back_populates='response', cascade='all, delete-orphan')
    artifact: Mapped['ResponseArtifact | None'] = relationship(back_populates='response', uselist=False, cascade='all, delete-orphan')

    @property
    def role_name(self) -> str:
        return self.artifact.role_name if self.artifact else ''

    @property
    def status(self) -> str:
        return self.artifact.status if self.artifact else 'completed'

    @property
    def error_detail(self) -> str:
        return self.artifact.error_detail if self.artifact else ''

    @property
    def response_type(self) -> str:
        return self.artifact.response_type if self.artifact else 'discussion'

    @property
    def average_user_rating(self) -> float | None:
        if not self.ratings:
            return None
        return round(sum(r.score for r in self.ratings) / len(self.ratings), 2)


class ResponseArtifact(Base):
    __tablename__ = 'response_artifacts'
    __table_args__ = (UniqueConstraint('response_id', name='uq_response_artifact_response_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey('model_responses.id', ondelete='CASCADE'), index=True)
    role_name: Mapped[str] = mapped_column(String(255), default='')
    status: Mapped[str] = mapped_column(String(20), default='completed', index=True)
    error_detail: Mapped[str] = mapped_column(Text, default='')
    response_type: Mapped[str] = mapped_column(String(30), default='discussion')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped['ModelResponse'] = relationship(back_populates='artifact')


class Evaluation(Base):
    __tablename__ = 'evaluations'
    __table_args__ = (UniqueConstraint('response_id', name='uq_evaluation_response_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey('model_responses.id', ondelete='CASCADE'), index=True)
    relevance: Mapped[float] = mapped_column(Float)
    coherence: Mapped[float] = mapped_column(Float)
    factuality: Mapped[float] = mapped_column(Float)
    usefulness: Mapped[float] = mapped_column(Float)
    engagement: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped['ModelResponse'] = relationship(back_populates='evaluations')
    detail: Mapped['EvaluationDetail | None'] = relationship(back_populates='evaluation', uselist=False, cascade='all, delete-orphan')


class EvaluationDetail(Base):
    __tablename__ = 'evaluation_details'
    __table_args__ = (UniqueConstraint('evaluation_id', name='uq_evaluation_detail_evaluation_id'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey('evaluations.id', ondelete='CASCADE'), index=True)
    overall_score: Mapped[float] = mapped_column(Float)
    role_adherence: Mapped[float] = mapped_column(Float)
    debate_quality: Mapped[float] = mapped_column(Float)
    evidence_quality: Mapped[float] = mapped_column(Float)
    improvement_score: Mapped[float] = mapped_column(Float)
    evaluation_mode: Mapped[str] = mapped_column(String(20), default='judge')
    judge_provider: Mapped[str] = mapped_column(String(50), default='')
    judge_model: Mapped[str] = mapped_column(String(100), default='')
    failure_tags_json: Mapped[str] = mapped_column(Text, default='[]')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evaluation: Mapped['Evaluation'] = relationship(back_populates='detail')

    @property
    def failure_tags(self) -> list[str]:
        try:
            data = json.loads(self.failure_tags_json or '[]')
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [str(item) for item in data if str(item).strip()]


class Rating(Base):
    __tablename__ = 'ratings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey('model_responses.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped['ModelResponse'] = relationship(back_populates='ratings')
    user: Mapped['User'] = relationship(back_populates='ratings')
