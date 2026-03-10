'use client';

import { useMemo, useState } from 'react';

import { Api, ModelResponse } from '@/services/api';

type Props = {
  responses: ModelResponse[];
};

function avgScore(response: ModelResponse): number | null {
  if (!response.evaluations.length) return null;
  const e = response.evaluations[0];
  return Number(((e.relevance + e.coherence + e.factuality + e.usefulness + e.engagement) / 5).toFixed(2));
}

export default function ResponseTree({ responses }: Props) {
  const [pendingId, setPendingId] = useState<number | null>(null);

  const grouped = useMemo(() => {
    const byParent = new Map<number | null, ModelResponse[]>();
    for (const r of responses) {
      const key = r.parent_response_id;
      const current = byParent.get(key) ?? [];
      current.push(r);
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
    const score = avgScore(node);

    return (
      <div key={node.id} className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" style={{ marginLeft: `${depth * 22}px` }}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">{node.model_name}</div>
            <div className="text-xs text-slate-400">Round {node.round_number}</div>
          </div>
          {score !== null && <div className="rounded-full bg-tide/15 px-3 py-1 text-xs font-semibold text-tide">Eval {score}</div>}
        </div>

        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{node.response_text}</p>

        <div className="mt-3 flex items-center gap-2 text-xs">
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
        </div>

        {children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  const roots = grouped.get(null) ?? [];
  return <div>{roots.map((root) => renderNode(root))}</div>;
}
