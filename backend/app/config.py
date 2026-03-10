from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'LLM Arena API'
    environment: str = 'development'
    debug: bool = True
    api_prefix: str = '/api/v1'

    database_url: str = 'mysql+asyncmy://root:root@localhost:3306/llm_arena'
    redis_url: str = 'redis://localhost:6379/0'

    jwt_secret_key: str = 'change-me'
    jwt_algorithm: str = 'HS256'
    jwt_expire_minutes: int = 60 * 24

    groq_api_key: str = ''
    gemini_api_key: str = ''
    mistral_api_key: str = ''
    huggingface_api_key: str = ''

    evaluator_provider: str = 'groq'
    evaluator_model: str = 'llama-3.1-8b-instant'

    max_conversation_rounds: int = 3
    skip_db_init: bool = False
    use_celery: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
