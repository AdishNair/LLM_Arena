from __future__ import annotations

import json
import re

from app.config import get_settings
from app.llm_clients.registry import get_client
from app.schemas import EvaluationResult

settings = get_settings()


class EvaluationEngine:
    async def evaluate(self, model_name: str, prompt: str, response_text: str) -> EvaluationResult:
        provider = settings.evaluator_provider
        evaluator_model = settings.evaluator_model

        rubric_prompt = (
            'Evaluate an LLM response from 1-10 for relevance, coherence, factuality, usefulness, engagement. '
            'Return ONLY JSON with keys relevance, coherence, factuality, usefulness, engagement, notes.\n\n'
            f'Prompt: {prompt}\n\nResponse from {model_name}:\n{response_text}'
        )

        try:
            evaluator_client = get_client(provider)
            raw = await evaluator_client.generate_response(model=evaluator_model, prompt=rubric_prompt, context=[])
            parsed = self._parse_result(raw)
            return EvaluationResult(model=model_name, **parsed)
        except Exception:
            heuristic = self._heuristic_eval(prompt, response_text)
            return EvaluationResult(model=model_name, **heuristic)

    def _parse_result(self, text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?', '', cleaned)
            cleaned = cleaned.replace('```', '').strip()

        data = json.loads(cleaned)
        return {
            'relevance': float(data.get('relevance', 5)),
            'coherence': float(data.get('coherence', 5)),
            'factuality': float(data.get('factuality', 5)),
            'usefulness': float(data.get('usefulness', 5)),
            'engagement': float(data.get('engagement', 5)),
            'notes': str(data.get('notes', '')),
        }

    def _heuristic_eval(self, prompt: str, response_text: str) -> dict:
        base = 6.0
        length_bonus = min(len(response_text) / 400.0, 2.0)
        relevance = base + (1.5 if any(w in response_text.lower() for w in prompt.lower().split()[:5]) else 0.3)
        coherence = base + min(length_bonus, 1.5)
        factuality = base
        usefulness = base + min(length_bonus, 1.0)
        engagement = base + 0.8 if '?' in response_text else base - 0.2

        def clamp(v: float) -> float:
            return float(max(1, min(10, round(v, 2))))

        return {
            'relevance': clamp(relevance),
            'coherence': clamp(coherence),
            'factuality': clamp(factuality),
            'usefulness': clamp(usefulness),
            'engagement': clamp(engagement),
            'notes': 'Heuristic fallback evaluation used.',
        }
