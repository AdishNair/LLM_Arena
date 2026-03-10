from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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


class Rating(Base):
    __tablename__ = 'ratings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey('model_responses.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped['ModelResponse'] = relationship(back_populates='ratings')
    user: Mapped['User'] = relationship(back_populates='ratings')
