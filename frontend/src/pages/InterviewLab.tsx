import React, { useState } from 'react';
import { LoaderCircle, PlayCircle, Send } from 'lucide-react';
import { api } from '../services/api';

interface Question {
  question_id: string;
  question: string;
  category: string;
  difficulty: string;
  sample_answer: string;
}

interface Session {
  session_id: string;
  role: string;
  questions: Question[];
}

export const InterviewLab: React.FC = () => {
  const [role, setRole] = useState('software_engineer');
  const [sessionType, setSessionType] = useState('technical');
  const [count, setCount] = useState(5);
  const [session, setSession] = useState<Session | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [evaluation, setEvaluation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await api.startInterviewSession({ role, session_type: sessionType, count });
      setSession(res.session);
      setEvaluation(null);
      setAnswers({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (q: Question) => {
    setError(null);
    setEvaluating(true);
    try {
      const res = await api.evaluateInterviewAnswer({
        question_id: q.question_id,
        question: q.question,
        sample_answer: q.sample_answer,
        candidate_answer: answers[q.question_id] || '',
        category: q.category,
        role,
      });
      setEvaluation(res.evaluation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to evaluate');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Interview Lab</h1>
        <p className="mt-2 text-sm text-slate-400">Practice with role-specific questions and get feedback.</p>
      </header>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm text-slate-300">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100">
              <option value="software_engineer">Software Engineer</option>
              <option value="frontend_developer">Frontend Developer</option>
              <option value="backend_developer">Backend Developer</option>
              <option value="data_scientist">Data Scientist</option>
              <option value="ml_engineer">ML Engineer</option>
              <option value="devops_engineer">DevOps Engineer</option>
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Session Type</label>
            <select value={sessionType} onChange={(e) => setSessionType(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100">
              <option value="technical">Technical</option>
              <option value="behavioral">Behavioral</option>
              <option value="mixed">Mixed</option>
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Questions</label>
            <input type="number" min={1} max={10} value={count} onChange={(e) => setCount(parseInt(e.target.value))} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" />
          </div>
        </div>
        <button onClick={startSession} disabled={loading} className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {loading ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
          Start Session
        </button>
        {error && <p className="text-sm text-rose-400">{error}</p>}
      </div>

      {session && (
        <div className="space-y-4">
          {session.questions?.map((q) => (
            <div key={q.question_id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
              <div>
                <span className="text-xs uppercase tracking-wider text-indigo-400">{q.category} • {q.difficulty}</span>
                <p className="mt-2 text-sm text-white">{q.question}</p>
              </div>
              <textarea
                value={answers[q.question_id] || ''}
                onChange={(e) => setAnswers({ ...answers, [q.question_id]: e.target.value })}
                placeholder="Type your answer..."
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 h-32"
              />
              <button onClick={() => submitAnswer(q)} disabled={evaluating} className="inline-flex items-center rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:border-indigo-500 disabled:opacity-50">
                <Send className="mr-1 h-3 w-3" /> Evaluate Answer
              </button>
            </div>
          ))}
        </div>
      )}

      {evaluation && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
          <h2 className="text-lg font-semibold text-white">Evaluation</h2>
          <p className="text-sm text-slate-400">Score: {evaluation.overall_score}/100 ({evaluation.rating})</p>
          {evaluation.strengths && <div><p className="text-sm font-semibold text-emerald-400">Strengths</p><ul className="mt-1 list-disc list-inside text-sm text-slate-300">{evaluation.strengths.map((s:string,i:number)=><li key={i}>{s}</li>)}</ul></div>}
          {evaluation.improvements && <div><p className="text-sm font-semibold text-amber-400">Improvements</p><ul className="mt-1 list-disc list-inside text-sm text-slate-300">{evaluation.improvements.map((s:string,i:number)=><li key={i}>{s}</li>)}</ul></div>}
          {evaluation.llm_feedback && <div><p className="text-sm font-semibold text-indigo-400">AI Feedback</p><p className="mt-1 text-sm text-slate-300 whitespace-pre-wrap">{evaluation.llm_feedback}</p></div>}
        </div>
      )}
    </div>
  );
};
