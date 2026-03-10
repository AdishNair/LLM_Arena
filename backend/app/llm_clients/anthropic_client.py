from __future__ import annotations

import httpx

from app.llm_clients.base_client import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    provider = 'anthropic'

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, model: str, prompt: str, context: list[dict] | None = None) -> str:
        if not self.api_key:
            raise RuntimeError('Anthropic API key not configured.')

        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }
        system = 'You are participating in a multi-model research debate. Be concise and evidence-aware.'
        content = []
        if context:
            flattened = '\n'.join([f"{m['role']}: {m['content']}" for m in context])
            content.append({'type': 'text', 'text': f'Context:\n{flattened}'})
        content.append({'type': 'text', 'text': prompt})

        payload = {
            'model': model,
            'max_tokens': 1000,
            'system': system,
            'messages': [{'role': 'user', 'content': content}],
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post('https://api.anthropic.com/v1/messages', headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        text_parts = [item['text'] for item in data.get('content', []) if item.get('type') == 'text']
        content = '\n'.join(text_parts).strip()
        if not content:
            raise RuntimeError('Anthropic returned an empty response.')
        return content
