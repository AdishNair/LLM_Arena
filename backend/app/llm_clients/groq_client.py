from __future__ import annotations

import httpx

from app.llm_clients.base_client import BaseLLMClient


class GroqClient(BaseLLMClient):
    provider = 'groq'

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, model: str, prompt: str, context: list[dict] | None = None) -> str:
        if not self.api_key:
            return 'Groq API key not configured.'

        messages = context[:] if context else []
        messages.append({'role': 'user', 'content': prompt})

        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        payload = {'model': model, 'messages': messages, 'temperature': 0.6}

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return data['choices'][0]['message']['content'].strip()
