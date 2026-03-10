import axios from 'axios';

export type Evaluation = {
  id: number;
  relevance: number;
  coherence: number;
  factuality: number;
  usefulness: number;
  engagement: number;
  notes: string;
};

export type ModelResponse = {
  id: number;
  thread_id: number;
  model_name: string;
  response_text: string;
  parent_response_id: number | null;
  round_number: number;
  created_at: string;
  evaluations: Evaluation[];
};

export type Thread = {
  id: number;
  title: string;
  prompt: string;
  user_id: number;
  subforum_id: number | null;
  created_at: string;
};

export type ThreadDetail = {
  thread: Thread;
  responses: ModelResponse[];
};

export type LeaderboardRow = {
  model_name: string;
  avg_relevance: number;
  avg_coherence: number;
  avg_factuality: number;
  avg_usefulness: number;
  avg_engagement: number;
  avg_overall: number;
  total_responses: number;
};

export type ThreadAnalytics = {
  thread_id: number;
  response_count: number;
  model_scores: LeaderboardRow[];
  agreement_index: number;
};

export type Subforum = {
  id: number;
  name: string;
  description: string;
  created_at: string;
};

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const Api = {
  async listThreads(): Promise<Thread[]> {
    const res = await api.get('/threads');
    return res.data;
  },
  async getThread(id: string): Promise<ThreadDetail> {
    const res = await api.get(`/threads/${id}`);
    return res.data;
  },
  async createThread(payload: {
    title: string;
    prompt: string;
    subforum_id?: number;
    selected_models: string[];
    allow_model_replies: boolean;
  }): Promise<Thread> {
    const res = await api.post('/threads/create', payload);
    return res.data;
  },
  async rerunThread(threadId: string, payload?: { selected_models?: string[]; allow_model_replies?: boolean }): Promise<Thread> {
    const res = await api.post(`/threads/${threadId}/rerun`, payload ?? {});
    return res.data;
  },
  async deleteThread(threadId: string): Promise<void> {
    await api.delete(`/threads/${threadId}`);
  },
  async rateResponse(response_id: number, score: number): Promise<void> {
    await api.post('/responses/rate', { response_id, score });
  },
  async leaderboard(): Promise<LeaderboardRow[]> {
    const res = await api.get('/analytics/leaderboard');
    return res.data;
  },
  async threadAnalytics(threadId: string): Promise<ThreadAnalytics> {
    const res = await api.get(`/analytics/thread/${threadId}`);
    return res.data;
  },
  async listSubforums(): Promise<Subforum[]> {
    const res = await api.get('/subforums');
    return res.data;
  },
  async register(payload: { username: string; email: string; password: string }): Promise<void> {
    await api.post('/auth/register', payload);
  },
  async login(payload: { email: string; password: string }): Promise<string> {
    const res = await api.post('/auth/login', payload);
    return res.data.access_token;
  },
};
