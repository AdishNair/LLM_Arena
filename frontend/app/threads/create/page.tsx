'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Api } from '@/services/api';

const defaultModels = ['groq:llama-3.1-8b-instant', 'mistral:mistral-small-latest', 'gemini:gemini-2.0-flash'];
const defaultRoles: Record<string, string> = {
  'groq:llama-3.1-8b-instant': 'Lead analyst focused on direct answers and decision-ready recommendations.',
  'mistral:mistral-small-latest': 'Skeptical reviewer focused on risks, gaps, and counterarguments.',
  'gemini:gemini-2.0-flash': 'Research synthesizer focused on structure, trade-offs, and missing context.',
};

export default function CreateThreadPage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([defaultModels[0], defaultModels[1]]);
  const [roles, setRoles] = useState<Record<string, string>>(defaultRoles);
  const [allowReplies, setAllowReplies] = useState(true);
  const [conversationRounds, setConversationRounds] = useState(4);
  const [includeSummary, setIncludeSummary] = useState(true);

  const toggleModel = (model: string) => {
    setSelectedModels((prev) => (prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model]));
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const created = await Api.createThread({
      title,
      prompt,
      participants: selectedModels.map((model_name) => ({
        model_name,
        role: roles[model_name] || 'General analyst',
      })),
      allow_model_replies: allowReplies,
      conversation_rounds: conversationRounds,
      include_summary: includeSummary,
    });
    router.push(`/threads/${created.id}`);
  };

  return (
    <section className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <h1 className="font-display text-2xl text-ink">Create Evaluation Thread</h1>
      <form onSubmit={onSubmit} className="mt-4 grid gap-4">
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

        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="font-semibold">Conversation Rounds</span>
            <input
              type="number"
              min={1}
              max={8}
              value={conversationRounds}
              onChange={(e) => setConversationRounds(Number(e.target.value))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>

          <div className="grid gap-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={allowReplies} onChange={(e) => setAllowReplies(e.target.checked)} />
              Allow models to react to peer responses
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={includeSummary} onChange={(e) => setIncludeSummary(e.target.checked)} />
              Add final synthesis summary
            </label>
          </div>
        </div>

        <div className="grid gap-3">
          <h2 className="text-sm font-semibold">Roles Per Model</h2>
          {selectedModels.map((model) => (
            <label key={model} className="grid gap-1 text-sm">
              <span className="font-medium text-slate-700">{model}</span>
              <textarea
                value={roles[model] || ''}
                onChange={(e) => setRoles((prev) => ({ ...prev, [model]: e.target.value }))}
                className="min-h-24 rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
          ))}
        </div>

        <button className="rounded-lg bg-pulse px-4 py-2 font-semibold text-white" type="submit" disabled={!selectedModels.length}>
          Launch Evaluation Thread
        </button>
      </form>
    </section>
  );
}
