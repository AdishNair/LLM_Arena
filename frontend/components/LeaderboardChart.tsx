'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { LeaderboardRow } from '@/services/api';

type Props = {
  data: LeaderboardRow[];
};

export default function LeaderboardChart({ data }: Props) {
  return (
    <div className="h-72 w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="model_name" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 10]} />
          <Tooltip />
          <Bar dataKey="blended_score" fill="#ff6b35" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
