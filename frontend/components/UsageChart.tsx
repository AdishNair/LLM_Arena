'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { LeaderboardRow } from '@/services/api';

type Props = {
  data: LeaderboardRow[];
};

export default function UsageChart({ data }: Props) {
  return (
    <div className="h-72 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="model_name" tick={{ fontSize: 10 }} />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="successful_responses" stroke="#2a9d8f" strokeWidth={3} />
          <Line type="monotone" dataKey="failed_responses" stroke="#e63946" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
