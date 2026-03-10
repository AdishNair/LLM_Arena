'use client';

import { FormEvent, useEffect, useState } from 'react';

import LeaderboardChart from '@/components/LeaderboardChart';
import UsageChart from '@/components/UsageChart';
import { Api, LeaderboardRow, ThreadAnalytics } from '@/services/api';

export default function AnalyticsPage() {
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [threadId, setThreadId] = useState('1');
  const [threadAnalytics, setThreadAnalytics] = useState<ThreadAnalytics | null>(null);

  useEffect(() => {
    Api.leaderboard().then(setLeaderboard).catch(() => setLeaderboard([]));
  }, []);

  const fetchThreadAnalytics = async (e: FormEvent) => {
    e.preventDefault();
    const result = await Api.threadAnalytics(threadId);
    setThreadAnalytics(result);
  };

  return (
    <section className="space-y-6">
      <h1 className="font-display text-3xl text-ink">Analytics Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <LeaderboardChart data={leaderboard} />
        <UsageChart data={leaderboard} />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
        <h2 className="font-display text-xl">Thread Agreement Analysis</h2>
        <form className="mt-3 flex gap-2" onSubmit={fetchThreadAnalytics}>
          <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" value={threadId} onChange={(e) => setThreadId(e.target.value)} placeholder="Thread ID" />
          <button className="rounded-lg bg-ink px-3 py-2 text-sm text-white">Analyze</button>
        </form>

        {threadAnalytics && (
          <div className="mt-4 space-y-2 text-sm">
            <div>Responses: {threadAnalytics.response_count}</div>
            <div>Agreement Index: {threadAnalytics.agreement_index}/10</div>
            <div className="rounded-lg bg-mist p-3">
              <div className="font-semibold">Conversation Summary</div>
              <div className="text-slate-600">
                {threadAnalytics.model_scores
                  .map((m) => `${m.model_name} avg ${m.avg_overall.toFixed(2)}`)
                  .join(' | ') || 'No responses evaluated yet.'}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
