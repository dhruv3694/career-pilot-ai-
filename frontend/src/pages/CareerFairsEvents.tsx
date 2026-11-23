import React, { useEffect, useState } from 'react';
import { Calendar, ExternalLink, MapPin } from 'lucide-react';
import { api } from '../services/api';

export const CareerFairsEvents: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCareerEvents().then((res) => {
      setEvents(res.events || []);
    }).catch((err) => setError(err instanceof Error ? err.message : 'Failed to load events')).finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-white">Career Fairs & Events</h1>
        <p className="mt-2 text-sm text-slate-400">Discover verified career fairs and networking events.</p>
      </header>

      {loading && <p className="text-sm text-slate-400">Loading events...</p>}
      {error && <p className="text-sm text-rose-400">{error}</p>}

      <div className="grid gap-4 md:grid-cols-2">
        {events.map((ev, idx) => (
          <div key={idx} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
            <h2 className="text-lg font-semibold text-white">{ev.title || ev.name}</h2>
            <p className="text-sm text-slate-400">{ev.organizer}</p>
            <div className="flex flex-wrap gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {ev.date} {ev.time || ''}</span>
              <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {ev.location || ev.format || 'TBD'}</span>
            </div>
            {ev.description && <p className="text-sm text-slate-300">{ev.description}</p>}
            {ev.registration_url && (
              <a href={ev.registration_url} target="_blank" rel="noreferrer" className="inline-flex items-center text-sm text-indigo-400 hover:text-indigo-300">
                Register <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            )}
            {ev.source_url && <p className="text-xs text-slate-600">Source: {ev.source_url}</p>}
          </div>
        ))}
      </div>
      {!loading && events.length === 0 && <p className="text-sm text-slate-400">No events found. Configure search sources or check backend.</p>}
    </div>
  );
};
