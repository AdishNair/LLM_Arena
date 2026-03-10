'use client';

import { useEffect, useState } from 'react';

import LeaderboardChart from '@/components/LeaderboardChart';
import { Api, LeaderboardRow } from '@/services/api';

export default function LeaderboardPage() {
  const [rows, setRows] = useState<LeaderboardRow[]>([]);

  useEffect(() => {
    Api.leaderboard().then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <section>
      <h1 className="font-display text-3xl text-ink">Model Leaderboard</h1>
      <div className="mt-5">
        <LeaderboardChart data={rows} />
      </div>
      <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="py-2">Model</th>
              <th>Blended</th>
              <th>Judge</th>
              <th>Role</th>
              <th>Debate</th>
              <th>Evidence</th>
              <th>Improve</th>
              <th>Success</th>
              <th>Fail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.model_name} className="border-t border-slate-100">
                <td className="py-2 font-semibold">{row.model_name}</td>
                <td>{row.blended_score.toFixed(2)}</td>
                <td>{row.avg_overall.toFixed(2)}</td>
                <td>{row.avg_role_adherence.toFixed(2)}</td>
                <td>{row.avg_debate_quality.toFixed(2)}</td>
                <td>{row.avg_evidence_quality.toFixed(2)}</td>
                <td>{row.avg_improvement_score.toFixed(2)}</td>
                <td>{row.successful_responses}</td>
                <td>{row.failed_responses}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
