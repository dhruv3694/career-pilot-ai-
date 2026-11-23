import React, { FormEvent, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Bookmark,
  BriefcaseBusiness,
  ExternalLink,
  LoaderCircle,
  MapPin,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api } from '../services/api';
import { JobItem, JobSearchResponse } from '../types';

type SourceFilter = 'all' | 'greenhouse' | 'lever' | 'web';

const sourceLabels: Record<string, string> = {
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  web: 'Web search',
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'The request could not be completed.';
}

function getSafeExternalUrl(value?: string): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
}

export const JobExplorer: React.FC = () => {
  const [query, setQuery] = useState('software engineer');
  const [location, setLocation] = useState('');
  const [workMode, setWorkMode] = useState('');
  const [source, setSource] = useState<SourceFilter>('all');
  const [result, setResult] = useState<JobSearchResponse | null>(null);
  const [savedJobs, setSavedJobs] = useState<JobItem[]>([]);
  const [showSaved, setShowSaved] = useState(false);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSavedJobs = async () => {
    const data = await api.getSavedJobs();
    setSavedJobs(data.saved_jobs ?? []);
  };

  useEffect(() => {
    loadSavedJobs().catch((loadError: unknown) => setError(getErrorMessage(loadError)));
  }, []);

  const runSearch = async () => {
    if (query.trim().length < 2) {
      setError('Enter at least two characters to search public job sources.');
      return;
    }

    setLoading(true);
    setError(null);
    setShowSaved(false);
    setSearched(true);
    try {
      const data = await api.searchJobs(query, location);
      if (workMode) data.jobs = data.jobs.filter((j:any) => j.work_mode === workMode || j.employment_type?.toLowerCase().includes(workMode));
      setResult(data);
      sessionStorage.setItem('careerpilot.recentJobs', JSON.stringify(data.jobs));
    } catch (searchError) {
      setResult(null);
      setError(getErrorMessage(searchError));
    } finally {
      setLoading(false);
    }
  };

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    void runSearch();
  };

  const toggleSaved = async (job: JobItem) => {
    setSavingId(job.id);
    setError(null);
    try {
      const isSaved = savedJobs.some((saved) => saved.id === job.id);
      if (isSaved) {
        await api.saveJob(job);
        setSavedJobs((jobs) => jobs.filter((saved) => saved.id !== job.id));
      } else {
        await api.saveJob(job);
        setSavedJobs((jobs) => [...jobs, job]);
      }
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setSavingId(null);
    }
  };

  const jobs = showSaved ? savedJobs : result?.jobs ?? [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 lg:p-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-300">
            <BriefcaseBusiness className="h-4 w-4" /> Public job discovery
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Job Explorer</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
            Search public Greenhouse and Lever career feeds. Listings are reported as found on a source, not guaranteed active or independently verified.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowSaved(true);
            setError(null);
            loadSavedJobs().catch((loadError: unknown) => setError(getErrorMessage(loadError)));
          }}
          className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
            showSaved
              ? 'border-indigo-500/50 bg-indigo-500/15 text-indigo-200'
              : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600'
          }`}
        >
          <Bookmark className="h-4 w-4" /> Saved jobs ({savedJobs.length})
        </button>
      </header>

      <form onSubmit={submitSearch} className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:grid-cols-2 xl:grid-cols-[minmax(220px,1.5fr)_minmax(160px,1fr)_150px_160px_auto]">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-slate-400">Role, skill or keyword</span>
          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 focus-within:border-indigo-500">
            <Search className="h-4 w-4 shrink-0 text-slate-500" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={120}
              className="w-full bg-transparent py-2.5 text-sm text-white outline-none placeholder:text-slate-600"
              placeholder="e.g. Python backend developer"
              aria-label="Role, skill or keyword"
            />
          </div>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-slate-400">Location</span>
          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 focus-within:border-indigo-500">
            <MapPin className="h-4 w-4 shrink-0 text-slate-500" />
            <input
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              maxLength={120}
              className="w-full bg-transparent py-2.5 text-sm text-white outline-none placeholder:text-slate-600"
              placeholder="Any location"
              aria-label="Location"
            />
          </div>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-slate-400">Work mode</span>
          <select
            value={workMode}
            onChange={(event) => setWorkMode(event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500"
            aria-label="Work mode"
          >
            <option value="">Any mode</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-slate-400">Source</span>
          <select
            value={source}
            onChange={(event) => setSource(event.target.value as SourceFilter)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500"
            aria-label="Job source"
          >
            <option value="all">All configured</option>
            <option value="greenhouse">Greenhouse boards</option>
            <option value="lever">Lever boards</option>
            <option value="web">SearXNG web</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={loading}
          className="mt-auto inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          Search
        </button>
      </form>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!showSaved && result?.errors.length ? (
        <div role="status" className="rounded-xl border border-amber-500/25 bg-amber-950/20 p-4">
          <div className="flex items-start gap-2 text-sm font-medium text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> Search notes
          </div>
          <ul className="mt-2 list-inside list-disc space-y-1 text-xs leading-relaxed text-amber-100/80">
            {result.errors.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
          </ul>
        </div>
      ) : null}

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">{showSaved ? 'Saved jobs' : 'Search results'}</h2>
            <p className="mt-1 text-xs text-slate-500">
              {showSaved
                ? `${savedJobs.length} saved listing${savedJobs.length === 1 ? '' : 's'}`
                : result
                  ? `${result.total_results} result${result.total_results === 1 ? '' : 's'} Â· Sources checked: ${result.sources_searched.map((name) => sourceLabels[name] ?? name).join(', ') || 'none'} Â· Retrieved ${new Date(result.retrieved_at).toLocaleString()}`
                  : 'Search live public feeds to retrieve current source results.'}
            </p>
          </div>
          {result && !showSaved && (
            <button
              type="button"
              onClick={() => void runSearch()}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh search
            </button>
          )}
        </div>

        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-sm text-slate-400">
            <LoaderCircle className="h-5 w-5 animate-spin text-indigo-400" /> Checking selected public sourcesâ€¦
          </div>
        )}

        {!loading && jobs.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {jobs.map((job) => {
              const isSaved = savedJobs.some((saved) => saved.id === job.id);
              const url = getSafeExternalUrl(job.original_url);
              return (
                <article key={job.id} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 transition-colors hover:border-slate-700">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold leading-snug text-white">{job.title}</h3>
                      <p className="mt-1 text-sm text-slate-300">{job.employer || job.company || 'Employer not identified'}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void toggleSaved(job)}
                      disabled={savingId === job.id}
                      aria-label={isSaved ? `Remove ${job.title} from saved jobs` : `Save ${job.title}`}
                      className={`rounded-lg border p-2 transition-colors disabled:opacity-50 ${
                        isSaved ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300' : 'border-slate-700 text-slate-400 hover:text-white'
                      }`}
                    >
                      {savingId === job.id ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Bookmark className="h-4 w-4" />}
                    </button>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs">
                    {job.location && <span className="rounded-md bg-slate-800 px-2.5 py-1 text-slate-300">{job.location}</span>}
                    {job.work_mode && <span className="rounded-md bg-slate-800 px-2.5 py-1 capitalize text-slate-300">{job.work_mode}</span>}
                    {job.source_name && <span className="rounded-md bg-slate-800 px-2.5 py-1 text-slate-300">{sourceLabels[job.source_name] ?? job.source_name}</span>}
                    {job.posted_at && <span className="rounded-md bg-slate-800 px-2.5 py-1 text-slate-400">Posted {new Date(job.posted_at).toLocaleDateString()}</span>}
                  </div>

                  <p className="mt-4 line-clamp-3 whitespace-pre-line text-sm leading-relaxed text-slate-400">
                    {job.description || 'The source did not provide a description.'}
                  </p>
                  <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
                    {job.verification_status === 'search_result_lead'
                      ? 'Search result lead â€” open the source and confirm the listing before applying.'
                      : 'Found on a public job board during this search; active status is not independently guaranteed.'}
                  </p>

                  <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-800 pt-4">
                    <span className="text-xs text-slate-500">
                      {job.required_skills?.length ? job.required_skills.slice(0, 4).join(' Â· ') : 'Skills not separately identified by source'}
                    </span>
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
                      >
                        View source <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-500">No source URL provided</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {!loading && jobs.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/25 p-10 text-center">
            <BriefcaseBusiness className="mx-auto h-8 w-8 text-slate-600" />
            <h3 className="mt-3 font-semibold text-slate-200">
              {showSaved ? 'No saved jobs yet' : searched ? 'No source listings found' : 'Start with a role or skill'}
            </h3>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-slate-500">
              {showSaved
                ? 'Save a listing from search results and it will appear here.'
                : searched
                  ? 'No sample postings are shown as substitutes. Try a broader search or another configured source. Optional web search requires a reachable SearXNG instance.'
                  : 'Results come from configured public feeds; availability depends on the connected employers and their current postings.'}
            </p>
          </div>
        )}
      </section>
    </div>
  );
};

