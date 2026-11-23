import React, { useState } from 'react';
import { Activity, LoaderCircle, Play } from 'lucide-react';
import { api } from '../services/api';

export const AgentControlCenter: React.FC = () => {
  const [targetRole, setTargetRole] = useState('Software Engineer');
  const [jobQuery, setJobQuery] = useState('software developer entry level');
  const [jobLocation, setJobLocation] = useState('Remote');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runWorkflow = async () => {
    setError(null);
    setRunning(true);
    try {
      const res = await api.runAgentWorkflow({ target_role: targetRole, job_query: jobQuery, job_location: jobLocation });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Workflow failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Agent Control Center</h1>
        <p className="mt-2 text-sm text-slate-400">Orchestrate multi-agent career intelligence workflow.</p>
      </header>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm text-slate-300">Target Role</label>
            <input value={targetRole} onChange={(e) => setTargetRole(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Job Query</label>
            <input value={jobQuery} onChange={(e) => setJobQuery(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" />
          </div>
          <div>
            <label className="mb-2 block text-sm text-slate-300">Location</label>
            <input value={jobLocation} onChange={(e) => setJobLocation(e.target.value)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100" />
          </div>
        </div>
        <button onClick={runWorkflow} disabled={running} className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {running ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
          Run Workflow
        </button>
        {error && <p className="text-sm text-rose-400">{error}</p>}
      </div>

      {result && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2"><Activity className="h-5 w-5" /> Run {result.run_id?.substring(0,8)}</h2>
            <p className="mt-1 text-sm text-slate-400">Status: {result.status} • Provider: {result.provider_used} • Fallback: {result.fallback_used ? 'Yes' : 'No'} • Time: {result.elapsed_seconds}s</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm">
              <div className="rounded-lg border border-slate-700 p-3"><p className="text-slate-400">Jobs</p><p className="text-white">{result.summary?.jobs_discovered || 0}</p></div>
              <div className="rounded-lg border border-slate-700 p-3"><p className="text-slate-400">Events</p><p className="text-white">{result.summary?.events_discovered || 0}</p></div>
              <div className="rounded-lg border border-slate-700 p-3"><p className="text-slate-400">Matches</p><p className="text-white">{result.summary?.matches_computed || 0}</p></div>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="text-sm font-semibold text-white mb-3">Agent Executions</h3>
            <div className="space-y-2">
              {result.agent_executions?.map((ex:any, idx:number) => (
                <div key={idx} className="rounded-lg border border-slate-700 p-3 text-sm">
                  <p className="text-white">{ex.agent}</p>
                  <p className="text-slate-400">Status: {ex.status} • Tools: {ex.tool_calls?.length || 0}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
