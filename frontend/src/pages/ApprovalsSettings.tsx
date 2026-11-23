import React, { useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import { api } from '../services/api';

export const ApprovalsSettings: React.FC = () => {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [providers, setProviders] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [a, p] = await Promise.all([api.getApprovals(), api.getProvidersStatus()]);
      setApprovals(a.approvals || []);
      setProviders(p);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const decide = async (id: string, decision: 'approve' | 'reject') => {
    await api.decideApproval(id, decision);
    load();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Approvals & Settings</h1>
        <p className="mt-2 text-sm text-slate-400">Manage approvals and configure providers.</p>
      </header>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Pending Approvals</h2>
        {loading && <p className="text-sm text-slate-400">Loading...</p>}
        <div className="space-y-3">
          {approvals.filter(a => a.status === 'pending').map((a) => (
            <div key={a.id} className="rounded-lg border border-slate-700 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">{a.title}</p>
                  <p className="mt-1 text-xs text-slate-400">{a.description}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => decide(a.id, 'approve')} className="inline-flex items-center rounded-lg bg-emerald-600 px-3 py-1 text-xs text-white hover:bg-emerald-500"><Check className="mr-1 h-3 w-3" /> Approve</button>
                  <button onClick={() => decide(a.id, 'reject')} className="inline-flex items-center rounded-lg bg-rose-600 px-3 py-1 text-xs text-white hover:bg-rose-500"><X className="mr-1 h-3 w-3" /> Reject</button>
                </div>
              </div>
            </div>
          ))}
        </div>
        {!loading && approvals.filter(a => a.status === 'pending').length === 0 && <p className="text-sm text-slate-400">No pending approvals.</p>}
      </div>

      {providers && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">LLM Provider Status</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {Object.entries(providers.providers || {}).map(([k,v]: [string,any]) => (
              <div key={k} className="rounded-lg border border-slate-700 p-3">
                <p className="text-sm font-semibold text-white capitalize">{k}</p>
                <p className="text-xs text-slate-400">Available: {v.available ? 'Yes' : 'No'} • Model: {v.model}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">Priority: {providers.active_priority?.join(' → ')}</p>
        </div>
      )}
    </div>
  );
};
