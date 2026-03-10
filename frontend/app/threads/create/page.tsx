'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Api } from '@/services/api';

const defaultModels = ['groq:llama-3.1-8b-instant', 'mistral:mistral-small-latest', 'gemini:gemini-2.0-flash'];

export default function CreateThreadPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([defaultModels[0]]);
  const [allowReplies, setAllowReplies] = useState(true);

  const toggleModel = (model: string) => {
    setSelectedModels((prev) => (prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model]));
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const created = await Api.createThread({
      title,
      prompt,
      selected_models: selectedModels,
      allow_model_replies: allowReplies,
    });
    router.push(`/threads/${created.id}`);
  };

  return (
    <section className="mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <h1 className="font-display text-2xl text-ink">Create Discussion Thread</h1>
      <form onSubmit={onSubmit} className="mt-4 grid gap-3">
        <input className="rounded-lg border border-slate-300 px-3 py-2" placeholder="Thread title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <textarea className="min-h-36 rounded-lg border border-slate-300 px-3 py-2" placeholder="Prompt for models" value={prompt} onChange={(e) => setPrompt(e.target.value)} required />

        <div>
          <label className="text-sm font-semibold">Participating Models</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {defaultModels.map((model) => (
              <button
                key={model}
                type="button"
                onClick={() => toggleModel(model)}
                className={`rounded-full px-3 py-1 text-xs ${selectedModels.includes(model) ? 'bg-ink text-white' : 'bg-mist text-slate-700'}`}
              >
                {model}
              </button>
            ))}
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={allowReplies} onChange={(e) => setAllowReplies(e.target.checked)} />
          Allow models to reply to other models (Round 2)
        </label>

        <button className="rounded-lg bg-pulse px-4 py-2 font-semibold text-white" type="submit" disabled={!selectedModels.length}>
          Launch Arena Thread
        </button>
      </form>
    </section>
  );
}



