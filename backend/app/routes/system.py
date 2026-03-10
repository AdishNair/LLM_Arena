import asyncio

from fastapi import APIRouter

from app.config import get_settings
from app.llm_clients.registry import get_client

router = APIRouter(prefix='/system', tags=['system'])
settings = get_settings()

PROVIDER_CHECKS: dict[str, dict[str, str]] = {
    'groq': {'model': 'llama-3.1-8b-instant', 'key_name': 'groq_api_key'},
    'gemini': {'model': 'gemini-2.0-flash', 'key_name': 'gemini_api_key'},
    'mistral': {'model': 'mistral-small-latest', 'key_name': 'mistral_api_key'},
    'huggingface': {'model': 'mistralai/Mistral-7B-Instruct-v0.3', 'key_name': 'huggingface_api_key'},
}


async def _check_provider(provider: str, model: str, key_name: str) -> dict:
    configured = bool(getattr(settings, key_name, ''))
    result = {
        'provider': provider,
        'model': model,
        'configured': configured,
        'reachable': False,
        'detail': 'API key not configured' if not configured else '',
    }

    if not configured:
        return result

    try:
        client = get_client(provider)
        response = await client.generate_response(model=model, prompt='Reply with OK only.', context=[])
        result['reachable'] = True
        result['detail'] = response[:120]
    except Exception as exc:
        result['detail'] = f'{type(exc).__name__}: {exc}'[:200]

    return result


@router.get('/providers/status')
async def provider_status() -> dict:
    checks = [
        _check_provider(provider, config['model'], config['key_name'])
        for provider, config in PROVIDER_CHECKS.items()
    ]
    providers = await asyncio.gather(*checks)
    return {'providers': providers}
