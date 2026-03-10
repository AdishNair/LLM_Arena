'use client';

import { FormEvent, useState } from 'react';

import { Api } from '@/services/api';

export default function AuthPanel() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [status, setStatus] = useState('');

  const onRegister = async (e: FormEvent) => {
    e.preventDefault();
    await Api.register({ username, email, password });
    setStatus('Registered. You can now login.');
  };

  const onLogin = async () => {
    const token = await Api.login({ email, password });
    localStorage.setItem('token', token);
    setStatus('Logged in. Auth token saved in browser localStorage.');
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <h2 className="font-display text-lg text-ink">Account</h2>
      <form className="mt-3 grid gap-2" onSubmit={onRegister}>
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <div className="flex gap-2">
          <button className="rounded-lg bg-ink px-3 py-2 text-sm font-semibold text-white" type="submit">Register</button>
          <button className="rounded-lg bg-pulse px-3 py-2 text-sm font-semibold text-white" type="button" onClick={onLogin}>Login</button>
        </div>
      </form>
      {status && <p className="mt-2 text-xs text-slate-600">{status}</p>}
    </div>
  );
}
