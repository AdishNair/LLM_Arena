from __future__ import annotations

import httpx

from app.llm_clients.base_client import BaseLLMClient


class HuggingFaceClient(BaseLLMClient):
    provider = 'huggingface'

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_response(self, model: str, prompt: str, context: list[dict] | None = None) -> str:
        if not self.api_key:
            return 'HuggingFace API key not configured.'

        headers = {'Authorization': f'Bearer {self.api_key}'}
        prompt_prefix = ''
        if context:
            prompt_prefix = '\n'.join([f"{m['role']}: {m['content']}" for m in context]) + '\n'

        payload = {
            'inputs': f'{prompt_prefix}user: {prompt}\nassistant:',
            'parameters': {'max_new_tokens': 600, 'temperature': 0.7},
        }
        url = f'https://api-inference.huggingface.co/models/{model}'

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list) and data:
            generated = data[0].get('generated_text', '')
            return generated.strip()
        if isinstance(data, dict) and data.get('generated_text'):
            return str(data['generated_text']).strip()
        return str(data)
