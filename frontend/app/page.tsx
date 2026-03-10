'use client';

import { useEffect, useState } from 'react';

import AuthPanel from '@/components/AuthPanel';
import ThreadCard from '@/components/ThreadCard';
import { Api, Thread } from '@/services/api';

export default function HomePage() {
  const [threads, setThreads] = useState<Thread[]>([]);

  useEffect(() => {
    Api.listThreads().then(setThreads).catch(() => setThreads([]));
  }, []);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.8fr,1fr]">
      <section>
        <h1 className="font-display text-3xl font-bold text-ink">Live Multi-Model Threads</h1>
        <p className="mt-2 text-sm text-slate-600">Post prompts and compare model behavior through threaded, auto-scored discussions.</p>
        <div className="mt-6 grid gap-4">
          {threads.map((thread) => (
            <ThreadCard key={thread.id} thread={thread} />
          ))}
          {!threads.length && <p className="text-sm text-slate-500">No threads yet.</p>}
        </div>
      </section>
      <aside>
        <AuthPanel />
      </aside>
    </div>
  );
}
