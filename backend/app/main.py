import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import Base, engine
from app.routes import analytics, auth, responses, subforums, system, threads

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def on_startup() -> None:
    if settings.skip_db_init:
        logging.warning('SKIP_DB_INIT=true, skipping database init check.')
        return

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except (OSError, SQLAlchemyError) as exc:
        logging.error('Database connection failed: %s', exc)
        raise RuntimeError(
            'Cannot connect to MySQL at DATABASE_URL. Start MySQL (or docker compose db) and retry.'
        ) from exc


@app.get('/health')
async def health() -> dict:
    return {'status': 'ok'}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(threads.router, prefix=settings.api_prefix)
app.include_router(responses.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(subforums.router, prefix=settings.api_prefix)
app.include_router(system.router, prefix=settings.api_prefix)


