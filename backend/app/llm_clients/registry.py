from app.config import get_settings
from app.llm_clients.base_client import BaseLLMClient
from app.llm_clients.gemini_client import GeminiClient
from app.llm_clients.groq_client import GroqClient
from app.llm_clients.huggingface_client import HuggingFaceClient
from app.llm_clients.mistral_client import MistralClient

settings = get_settings()

CLIENTS: dict[str, BaseLLMClient] = {
    'groq': GroqClient(settings.groq_api_key),
    'gemini': GeminiClient(settings.gemini_api_key),
    'mistral': MistralClient(settings.mistral_api_key),
    'huggingface': HuggingFaceClient(settings.huggingface_api_key),
}


def split_model_identifier(model_identifier: str) -> tuple[str, str]:
    if ':' not in model_identifier:
        raise ValueError('Model identifier must be in provider:model format')
    provider, model = model_identifier.split(':', 1)
    if provider not in CLIENTS:
        raise ValueError(f'Unsupported provider: {provider}')
    return provider, model


def get_client(provider: str) -> BaseLLMClient:
    client = CLIENTS.get(provider)
    if not client:
        raise ValueError(f'Unsupported provider: {provider}')
    return client
