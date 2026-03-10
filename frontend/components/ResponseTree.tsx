'use client';

import { useMemo, useState } from 'react';

import { Api, ModelResponse } from '@/services/api';

type Props = {
  responses: ModelResponse[];
};

function overallScore(response: ModelResponse): number | null {
  const detail = response.evaluations[0]?.detail;
  return detail ? Number(detail.overall_score.toFixed(2)) : null;
}

export default function ResponseTree({ responses }: Props) {
  const [pendingId, setPendingId] = useState<number | null>(null);

  const grouped = useMemo(() => {
    const byParent = new Map<number | null, ModelResponse[]>();
    for (const response of responses) {
      const key = response.parent_response_id;
      const current = byParent.get(key) ?? [];
      current.push(response);
      byParent.set(key, current);
    }
    return byParent;
  }, [responses]);

  const handleRate = async (responseId: number, score: number) => {
    try {
      setPendingId(responseId);
      await Api.rateResponse(responseId, score);
    } finally {
      setPendingId(null);
    }
  };

  const renderNode = (node: ModelResponse, depth = 0) => {
    const children = grouped.get(node.id) ?? [];
    const score = overallScore(node);
    const detail = node.evaluations[0]?.detail;
    const canRate = node.status === 'completed' && node.response_type !== 'summary';

    return (
      <div key={node.id} className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" style={{ marginLeft: `${depth * 22}px` }}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">{node.model_name}</div>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-400">
              <span>Round {node.round_number}</span>
              {node.role_name && <span>Role: {node.role_name}</span>}
              <span className={node.status === 'completed' ? 'text-emerald-600' : 'text-red-600'}>{node.status}</span>
              {node.response_type !== 'discussion' && <span>{node.response_type}</span>}
            </div>
          </div>
          {score !== null && <div className="rounded-full bg-tide/15 px-3 py-1 text-xs font-semibold text-tide">Eval {score}</div>}
        </div>

        {node.status === 'completed' ? (
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{node.response_text}</p>
        ) : (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Generation failed and was excluded from evaluation.
            {node.error_detail ? <div className="mt-2 text-xs">{node.error_detail}</div> : null}
          </div>
        )}

        {detail ? (
          <div className="mt-3 grid gap-2 rounded-lg bg-mist p-3 text-xs text-slate-700 md:grid-cols-2">
            <div>Role adherence: {detail.role_adherence.toFixed(2)}</div>
            <div>Debate quality: {detail.debate_quality.toFixed(2)}</div>
            <div>Evidence quality: {detail.evidence_quality.toFixed(2)}</div>
            <div>Improvement: {detail.improvement_score.toFixed(2)}</div>
            <div>Judge: {detail.judge_provider}:{detail.judge_model}</div>
            <div>Mode: {detail.evaluation_mode}</div>
            {detail.failure_tags.length ? <div className="md:col-span-2">Failure tags: {detail.failure_tags.join(', ')}</div> : null}
          </div>
        ) : null}

        {canRate ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">Rate response:</span>
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                disabled={pendingId === node.id}
                onClick={() => handleRate(node.id, star)}
                className="rounded-full border border-slate-300 px-2 py-1 hover:bg-mist"
              >
                {star}
              </button>
            ))}
            {node.average_user_rating !== null ? <span className="text-slate-500">Avg user rating: {node.average_user_rating.toFixed(2)}</span> : null}
          </div>
        ) : null}

        {children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  const roots = grouped.get(null) ?? [];
  return <div>{roots.map((root) => renderNode(root))}</div>;
}
