'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import ResponseTree from '@/components/ResponseTree';
import { Api, ThreadAnalytics, ThreadDetail } from '@/services/api';

type Props = {
  params: { id: string };
};

export default function ThreadViewPage({ params }: Props) {
  const router = useRouter();
  const [thread, setThread] = useState<ThreadDetail | null>(null);
  const [analytics, setAnalytics] = useState<ThreadAnalytics | null>(null);
  const [actionState, setActionState] = useState<'idle' | 'rerunning' | 'deleting'>('idle');
  const [status, setStatus] = useState('');

  useEffect(() => {
    Api.getThread(params.id).then(setThread);
    Api.threadAnalytics(params.id).then(setAnalytics).catch(() => setAnalytics(null));

    const timer = setInterval(() => {
      Api.getThread(params.id).then(setThread).catch(() => undefined);
      Api.threadAnalytics(params.id).then(setAnalytics).catch(() => undefined);
    }, 6000);

    return () => clearInterval(timer);
  }, [params.id]);

  const onRerun = async () => {
    try {
      setActionState('rerunning');
      setStatus('Rerun started. Refreshing responses shortly...');
      await Api.rerunThread(params.id);
    } catch {
      setStatus('Rerun failed. Ensure you are logged in as thread owner.');
    } finally {
      setActionState('idle');
    }
  };

  const onDelete = async () => {
    try {
      setActionState('deleting');
      await Api.deleteThread(params.id);
      router.push('/');
    } catch {
      setStatus('Delete failed. Ensure you are logged in as thread owner.');
      setActionState('idle');
    }
  };

  if (!thread) return <p>Loading thread...</p>;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.8fr,1fr]">
      <section>
        <h1 className="font-display text-3xl font-bold text-ink">{thread.thread.title}</h1>
        <p className="mt-2 rounded-xl bg-white p-4 text-slate-700 shadow-card">{thread.thread.prompt}</p>

        <div className="mt-4 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-card md:grid-cols-2">
          <div className="text-sm text-slate-600">
            <div>Conversation rounds: {thread.thread.conversation_rounds}</div>
            <div>Peer replies: {thread.thread.allow_model_replies ? 'Enabled' : 'Disabled'}</div>
            <div>Final summary: {thread.thread.include_summary ? 'Enabled' : 'Disabled'}</div>
          </div>
          <div className="space-y-1 text-sm text-slate-600">
            {thread.thread.participants.map((participant) => (
              <div key={participant.model_name}>
                <span className="font-semibold text-ink">{participant.model_name}</span>: {participant.role}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRerun}
            disabled={actionState !== 'idle'}
            className="rounded-lg bg-ink px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {actionState === 'rerunning' ? 'Rerunning...' : 'Rerun Thread'}
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={actionState !== 'idle'}
            className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {actionState === 'deleting' ? 'Deleting...' : 'Delete Thread'}
          </button>
        </div>
        {status && <p className="mt-2 text-xs text-slate-500">{status}</p>}

        <h2 className="mt-6 font-display text-xl">Arena Responses</h2>
        <ResponseTree responses={thread.responses} />
      </section>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
          <h3 className="font-display text-lg">Thread Analytics</h3>
          <p className="mt-2 text-sm text-slate-600">Responses: {analytics?.response_count ?? 0}</p>
          <p className="text-sm text-slate-600">Successful: {analytics?.successful_response_count ?? 0}</p>
          <p className="text-sm text-slate-600">Failed: {analytics?.failed_response_count ?? 0}</p>
          <p className="text-sm text-slate-600">Max round reached: {analytics?.max_round_reached ?? '-'}</p>
          <p className="text-sm text-slate-600">Agreement Index: {analytics?.agreement_index ?? '-'} / 10</p>
          <p className="mt-3 text-sm text-slate-700">{analytics?.thread_summary ?? 'Waiting for evaluated responses.'}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
          <h3 className="font-display text-lg">Model Averages</h3>
          <div className="mt-3 space-y-2">
            {(analytics?.model_scores ?? []).map((row) => (
              <div key={row.model_name} className="rounded-lg bg-mist p-3 text-xs text-slate-700">
                <div className="font-semibold text-ink">{row.model_name}</div>
                <div>Blended: {row.blended_score.toFixed(2)}</div>
                <div>Judge overall: {row.avg_overall.toFixed(2)}</div>
                <div>Role adherence: {row.avg_role_adherence.toFixed(2)}</div>
                <div>Debate quality: {row.avg_debate_quality.toFixed(2)}</div>
                <div>Evidence quality: {row.avg_evidence_quality.toFixed(2)}</div>
                <div>Improvement: {row.avg_improvement_score.toFixed(2)}</div>
                <div>
                  Success / Fail: {row.successful_responses} / {row.failed_responses}
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
