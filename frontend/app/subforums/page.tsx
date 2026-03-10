'use client';

import { useEffect, useState } from 'react';

import { Api, Subforum } from '@/services/api';

export default function SubforumsPage() {
  const [items, setItems] = useState<Subforum[]>([]);

  useEffect(() => {
    Api.listSubforums().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <section>
      <h1 className="font-display text-3xl text-ink">Subforums</h1>
      <p className="mt-2 text-sm text-slate-600">Research tracks to organize domain-specific arena threads.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
            <h2 className="font-display text-xl">{item.name}</h2>
            <p className="mt-2 text-sm text-slate-600">{item.description || 'No description yet.'}</p>
          </article>
        ))}
        {!items.length && <p className="text-sm text-slate-500">No subforums available.</p>}
      </div>
    </section>
  );
}
