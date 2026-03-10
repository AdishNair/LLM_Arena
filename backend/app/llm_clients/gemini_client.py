from __future__ import annotations

import httpx

from app.llm_clients.base_client import BaseLLMClient


class GeminiClient(BaseLLMClient):
    provider = 'gemini'

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, model: str, prompt: str, context: list[dict] | None = None) -> str:
        if not self.api_key:
            return 'Gemini API key not configured.'

        parts: list[dict[str, str]] = []
        if context:
            flattened = '\n'.join([f"{message['role']}: {message['content']}" for message in context])
            parts.append({'text': f'Context:\n{flattened}'})
        parts.append({'text': prompt})

        payload = {
            'contents': [{'parts': parts}],
            'generationConfig': {'temperature': 0.6},
        }
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}'

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get('candidates', [])
        if not candidates:
            return 'Gemini returned no candidates.'

        text_parts = candidates[0].get('content', {}).get('parts', [])
        return '\n'.join(part.get('text', '') for part in text_parts).strip()
