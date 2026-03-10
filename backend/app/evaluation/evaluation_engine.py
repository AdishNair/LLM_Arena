from __future__ import annotations

import json
import re

from app.config import get_settings
from app.llm_clients.registry import get_client
from app.schemas import EvaluationResult

settings = get_settings()


class EvaluationEngine:
    async def evaluate(
        self,
        model_name: str,
        prompt: str,
        response_text: str,
        role_name: str = '',
        previous_response_text: str | None = None,
        response_type: str = 'discussion',
    ) -> EvaluationResult:
        provider = settings.evaluator_provider
        evaluator_model = settings.evaluator_model

        prior_response_block = previous_response_text if previous_response_text else 'No previous response from this model.'
        rubric_prompt = (
            'You are judging a model response in a multi-model evaluation harness.\n'
            'Score each field from 1 to 10 and return ONLY valid JSON with keys: '
            'relevance, coherence, factuality, usefulness, engagement, role_adherence, debate_quality, '
            'evidence_quality, improvement_score, failure_tags, notes.\n\n'
            f'User prompt:\n{prompt}\n\n'
            f'Model:\n{model_name}\n\n'
            f'Response type:\n{response_type}\n\n'
            f'Assigned role:\n{role_name or "No explicit role assigned."}\n\n'
            f'Previous response from this same model:\n{prior_response_block}\n\n'
            f'Current response:\n{response_text}\n'
        )

        try:
            evaluator_client = get_client(provider)
            raw = await evaluator_client.generate_response(model=evaluator_model, prompt=rubric_prompt, context=[])
            parsed = self._parse_result(raw)
            parsed['overall_score'] = self._overall(parsed)
            parsed['evaluation_mode'] = 'judge'
            parsed['judge_provider'] = provider
            parsed['judge_model'] = evaluator_model
            return EvaluationResult(model=model_name, **parsed)
        except Exception:
            heuristic = self._heuristic_eval(prompt, response_text, role_name, previous_response_text)
            heuristic['overall_score'] = self._overall(heuristic)
            heuristic['evaluation_mode'] = 'heuristic'
            heuristic['judge_provider'] = provider
            heuristic['judge_model'] = evaluator_model
            return EvaluationResult(model=model_name, **heuristic)

    def _parse_result(self, text: str) -> dict:
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?', '', cleaned)
            cleaned = cleaned.replace('```', '').strip()

        data = json.loads(cleaned)
        return {
            'relevance': self._float_score(data.get('relevance', 5)),
            'coherence': self._float_score(data.get('coherence', 5)),
            'factuality': self._float_score(data.get('factuality', 5)),
            'usefulness': self._float_score(data.get('usefulness', 5)),
            'engagement': self._float_score(data.get('engagement', 5)),
            'role_adherence': self._float_score(data.get('role_adherence', 5)),
            'debate_quality': self._float_score(data.get('debate_quality', 5)),
            'evidence_quality': self._float_score(data.get('evidence_quality', 5)),
            'improvement_score': self._float_score(data.get('improvement_score', 5)),
            'failure_tags': self._parse_failure_tags(data.get('failure_tags', [])),
            'notes': str(data.get('notes', '')),
        }

    def _heuristic_eval(
        self,
        prompt: str,
        response_text: str,
        role_name: str,
        previous_response_text: str | None,
    ) -> dict:
        prompt_words = [word for word in re.findall(r'\w+', prompt.lower()) if len(word) > 3]
        response_lower = response_text.lower()
        role_words = [word for word in re.findall(r'\w+', role_name.lower()) if len(word) > 3]
        base = 5.5
        length_bonus = min(len(response_text) / 500.0, 2.0)
        prompt_overlap = sum(1 for word in prompt_words[:8] if word in response_lower)
        role_overlap = sum(1 for word in role_words[:6] if word in response_lower)
        has_structure = 0.8 if any(token in response_text for token in ['\n-', '\n1.', ':']) else 0.0
        has_uncertainty = 0.6 if any(token in response_lower for token in ['uncertain', 'likely', 'depends', 'trade-off']) else 0.0
        mentions_evidence = 0.8 if any(token in response_lower for token in ['because', 'evidence', 'source', 'data', 'benchmark']) else 0.0
        improvement_signal = 0.0
        if previous_response_text:
            prior_len = max(len(previous_response_text), 1)
            improvement_signal = min(max((len(response_text) - prior_len) / prior_len, -0.5), 0.5) * 4

        def clamp(value: float) -> float:
            return float(max(1, min(10, round(value, 2))))

        relevance = clamp(base + min(prompt_overlap * 0.7, 2.5))
        coherence = clamp(base + length_bonus + has_structure)
        factuality = clamp(base + has_uncertainty + mentions_evidence * 0.5)
        usefulness = clamp(base + length_bonus + min(prompt_overlap * 0.3, 1.0))
        engagement = clamp(base + (0.7 if '?' in response_text else 0.0) + (0.5 if len(response_text) > 220 else 0.0))
        role_adherence = clamp(base + min(role_overlap * 0.9, 2.5))
        debate_quality = clamp(base + has_structure + mentions_evidence)
        evidence_quality = clamp(base + mentions_evidence + has_uncertainty)
        improvement_score = clamp(base + improvement_signal)

        return {
            'relevance': relevance,
            'coherence': coherence,
            'factuality': factuality,
            'usefulness': usefulness,
            'engagement': engagement,
            'role_adherence': role_adherence,
            'debate_quality': debate_quality,
            'evidence_quality': evidence_quality,
            'improvement_score': improvement_score,
            'failure_tags': [],
            'notes': 'Heuristic fallback evaluation used.',
        }

    def _overall(self, scores: dict) -> float:
        values = [
            scores['relevance'],
            scores['coherence'],
            scores['factuality'],
            scores['usefulness'],
            scores['engagement'],
            scores['role_adherence'],
            scores['debate_quality'],
            scores['evidence_quality'],
            scores['improvement_score'],
        ]
        return round(sum(values) / len(values), 2)

    def _float_score(self, value: object) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 5.0
        return float(max(1, min(10, round(score, 2))))

    def _parse_failure_tags(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(',') if part.strip()]
        return []
