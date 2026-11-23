import React, { useEffect, useState } from 'react';
import { Trash2, Edit } from 'lucide-react';
import { api } from '../services/api';

export const MemoryPrivacy: React.FC = () => {
  const [memories, setMemories] = useState<any[]>([]);
  const [preferences, setPreferences] = useState<any>({});
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [m, p] = await Promise.all([api.getMemory(), api.getPreferences()]);
      setMemories(m.memories || []);
      setPreferences(p.preferences || {});
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const deleteMemory = async (id: string) => {
    await api.deleteMemory(id);
    load();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Memory & Privacy</h1>
        <p className="mt-2 text-sm text-slate-400">Manage stored data and privacy controls.</p>
      </header>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Stored Memories</h2>
        {loading && <p className="text-sm text-slate-400">Loading...</p>}
        <div className="space-y-2">
          {memories.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-lg border border-slate-700 p-3">
              <div>
                <p className="text-sm text-white">{m.key || m.category}</p>
                <p className="text-xs text-slate-400">{typeof m.value === 'string' ? m.value : JSON.stringify(m.value)}</p>
              </div>
              <button onClick={() => deleteMemory(m.id)} className="text-rose-400 hover:text-rose-300"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
        {!loading && memories.length === 0 && <p className="text-sm text-slate-400">No memories stored.</p>}
      </div>
    </div>
  );
};
