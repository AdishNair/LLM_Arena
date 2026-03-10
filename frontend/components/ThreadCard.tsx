import Link from 'next/link';

import { Thread } from '@/services/api';

type Props = {
  thread: Thread;
};

export default function ThreadCard({ thread }: Props) {
  return (
    <Link href={`/threads/${thread.id}`} className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-card transition hover:-translate-y-0.5">
      <h3 className="font-display text-lg font-medium text-ink">{thread.title}</h3>
      <p className="mt-2 max-h-16 overflow-hidden text-sm text-slate-600">{thread.prompt}</p>
      <div className="mt-3 text-xs text-slate-500">Thread #{thread.id}</div>
    </Link>
  );
}
