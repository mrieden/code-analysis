import React, { useEffect, useState } from 'react';
import { Page } from '../types';
import { calculateGlobalScore } from './Results';

interface Repo {
  name: string;
  full_name: string;
  owner: string;
  private: boolean;
  default_branch: string;
}

interface FileResult {
  path: string;
  language: 'python' | 'cpp' | 'java' | string;
  supported: boolean;
  loc?: number;
  analysis?: any;
  error?: string;
}

interface RepoAnalysisResult {
  owner: string;
  repo: string;
  branch: string;
  total_files: number;
  language_counts: Record<string, number>;
  truncated: boolean;
  files: FileResult[];
}

interface RepoAnalysisProps {
  token: string | null;
  onNavigate: (page: Page) => void;
  onOpenInEditor: (content: string) => void;
}

const API = 'http://localhost:8000';

const scoreColor = (s: number) =>
  s >= 80 ? 'text-green-400' : s >= 50 ? 'text-yellow-400' : 'text-red-400';
const scoreBar = (s: number) =>
  s >= 80 ? 'bg-green-400' : s >= 50 ? 'bg-yellow-400' : 'bg-red-400';

const LANG_LABEL: Record<string, string> = {
  python: 'Python',
  cpp: 'C++',
  java: 'Java',
};

const langBadgeClass = (lang: string) => {
  if (lang === 'python') return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
  if (lang === 'cpp') return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
  if (lang === 'java') return 'bg-orange-500/15 text-orange-300 border-orange-500/30';
  return 'bg-text-secondary/10 text-text-secondary border-border-color';
};

const LangBadge: React.FC<{ lang: string }> = ({ lang }) => (
  <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${langBadgeClass(lang)}`}>
    {LANG_LABEL[lang] || lang}
  </span>
);

const RepoAnalysis: React.FC<RepoAnalysisProps> = ({ token, onNavigate, onOpenInEditor }) => {
  const [repos, setRepos]               = useState<Repo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [analyzing, setAnalyzing]       = useState(false);
  const [result, setResult]             = useState<RepoAnalysisResult | null>(null);
  const [activeRepo, setActiveRepo]     = useState<Repo | null>(null);
  const [error, setError]               = useState('');
  const [sortKey, setSortKey]           = useState<'score' | 'path' | 'violations'>('score');
  const [opening, setOpening]           = useState<string | null>(null);

  const authHeaders: Record<string, string> | undefined =
    token ? { Authorization: `Bearer ${token}` } : undefined;

  useEffect(() => {
    if (!token) return;
    setLoadingRepos(true);
    setError('');
    fetch(`${API}/github/repos`, { headers: authHeaders })
      .then((r) => { if (!r.ok) throw new Error('Could not load your repositories.'); return r.json(); })
      .then((d: Repo[]) => setRepos(d))
      .catch((e) => setError(e.message))
      .finally(() => setLoadingRepos(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const analyze = (repo: Repo) => {
    setActiveRepo(repo);
    setAnalyzing(true);
    setResult(null);
    setError('');
    fetch(`${API}/github/analyze-repo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(authHeaders || {}) },
      body: JSON.stringify({ owner: repo.owner, repo: repo.name }),
    })
      .then((r) => { if (!r.ok) throw new Error('Repository analysis failed.'); return r.json(); })
      .then((d: RepoAnalysisResult) => setResult(d))
      .catch((e) => setError(e.message || 'Repository analysis failed.'))
      .finally(() => setAnalyzing(false));
  };

  const openFile = (path: string) => {
    if (!activeRepo) return;
    setOpening(path);
    fetch(
      `${API}/github/file?owner=${encodeURIComponent(activeRepo.owner)}` +
        `&repo=${encodeURIComponent(activeRepo.name)}&path=${encodeURIComponent(path)}`,
      { headers: authHeaders },
    )
      .then((r) => { if (!r.ok) throw new Error('Could not open file.'); return r.json(); })
      .then((d: { content: string }) => onOpenInEditor(d.content ?? ''))
      .catch((e) => setError(e.message))
      .finally(() => setOpening(null));
  };

  const files = result?.files || [];

  // Python files carry a full analysis; we score those.
  const scored = files
    .filter((f) => f.analysis && !f.error)
    .map((f) => ({
      ...f,
      score: calculateGlobalScore(f.analysis),
      violations: f.analysis?.total_violations ?? 0,
    }));

  const avgScore = scored.length
    ? Math.round(scored.reduce((a, f) => a + f.score, 0) / scored.length)
    : 0;
  const cleanFiles = scored.filter((f) => f.violations === 0).length;
  const totalViolations = scored.reduce((a, f) => a + f.violations, 0);
  const worst = [...scored].sort((a, b) => a.score - b.score)[0];

  // Rows include every detected file (analyzed or pending) so multi-language
  // repos surface their C++/Java files too.
  type Row = FileResult & { score: number | null; violations: number | null };
  const rows: Row[] = files.map((f) => {
    if (f.analysis && !f.error) {
      return { ...f, score: calculateGlobalScore(f.analysis), violations: f.analysis?.total_violations ?? 0 };
    }
    return { ...f, score: null, violations: null };
  });

  const sortedRows = [...rows].sort((a, b) => {
    if (sortKey === 'path') return a.path.localeCompare(b.path);
    if (sortKey === 'violations') return (b.violations ?? -1) - (a.violations ?? -1);
    // score: analyzed files first (lowest score first), pending files last
    if (a.score === null && b.score === null) return a.path.localeCompare(b.path);
    if (a.score === null) return 1;
    if (b.score === null) return -1;
    return a.score - b.score;
  });

  const counts = result?.language_counts || {};
  const pendingCount = files.filter((f) => !f.supported && !f.error).length;

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow py-16 gap-4">
        <p className="text-text-secondary">Sign in to scan a repository.</p>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline">← Back</button>
      </div>
    );
  }

  return (
    <div className="flex flex-col py-6 gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-text-secondary hover:text-text-primary transition-colors">← Back</button>
          <h1 className="text-2xl font-bold text-text-primary">Repository Scan</h1>
        </div>
        {result && (
          <button onClick={() => { setResult(null); setActiveRepo(null); }} className="text-sm text-accent-primary hover:underline">Scan another repo</button>
        )}
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
      )}

      {/* Repo picker */}
      {!result && !analyzing && (
        <div className="bg-ui-panels border border-border-color rounded-xl p-5">
          <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-4">Choose a repository</h2>
          {loadingRepos ? (
            <div className="flex justify-center py-10"><div className="w-8 h-8 border-4 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[60vh] overflow-y-auto">
              {repos.map((repo) => (
                <button
                  key={repo.full_name}
                  onClick={() => analyze(repo)}
                  className="text-left px-4 py-3 rounded-lg border border-border-color hover:border-accent-primary/50 hover:bg-accent-primary/5 transition-all flex items-center justify-between gap-2"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-text-primary truncate">{repo.name}</span>
                    <span className="block text-xs text-text-secondary truncate">{repo.owner}</span>
                  </span>
                  {repo.private && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-border-color text-text-secondary shrink-0">Private</span>}
                </button>
              ))}
              {repos.length === 0 && <p className="text-sm text-text-secondary py-6 text-center col-span-full">No repositories found.</p>}
            </div>
          )}
        </div>
      )}

      {/* Analyzing */}
      {analyzing && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="w-12 h-12 border-4 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin" />
          <p className="text-text-primary font-bold">Scanning {activeRepo?.name}…</p>
          <p className="text-text-secondary text-sm text-center max-w-md">Fetching files concurrently and running static analysis on every Python file. C++ and Java files are detected for on-demand deep analysis.</p>
        </div>
      )}

      {/* Results */}
      {result && !analyzing && (
        <>
          {/* Aggregate */}
          <div className="bg-ui-panels border border-border-color rounded-xl p-6">
            <div className="flex items-center justify-between mb-5 flex-wrap gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary">{result.owner}/{result.repo} · {result.branch}</h2>
              {result.truncated && <span className="text-xs text-yellow-400">Showing first {result.total_files} files</span>}
            </div>

            {/* Language breakdown */}
            <div className="flex flex-wrap items-center gap-2 mb-5">
              {Object.keys(counts).length > 0 ? (
                Object.entries(counts).map(([lang, n]) => (
                  <span key={lang} className="flex items-center gap-1.5">
                    <LangBadge lang={lang} />
                    <span className="text-xs text-text-secondary">{n} file{n === 1 ? '' : 's'}</span>
                  </span>
                ))
              ) : (
                <span className="text-xs text-text-secondary">No supported code files detected.</span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className={`text-4xl font-bold font-mono ${scoreColor(avgScore)}`}>{avgScore}</p>
                <p className="text-xs text-text-secondary mt-1">Avg Python Score</p>
              </div>
              <div className="text-center">
                <p className="text-4xl font-bold font-mono text-accent-primary">{scored.length}</p>
                <p className="text-xs text-text-secondary mt-1">Python Analyzed</p>
              </div>
              <div className="text-center">
                <p className="text-4xl font-bold font-mono text-green-400">{cleanFiles}</p>
                <p className="text-xs text-text-secondary mt-1">SOLID-Clean Files</p>
              </div>
              <div className="text-center">
                <p className={`text-4xl font-bold font-mono ${totalViolations > 0 ? 'text-red-400' : 'text-green-400'}`}>{totalViolations}</p>
                <p className="text-xs text-text-secondary mt-1">Total Violations</p>
              </div>
            </div>
            {worst && (
              <p className="text-xs text-text-secondary mt-5 text-center">
                Lowest scoring file: <span className="font-mono text-red-300">{worst.path}</span> ({worst.score}/100)
              </p>
            )}
            {pendingCount > 0 && (
              <p className="text-xs text-text-secondary mt-2 text-center">
                {pendingCount} C++/Java file{pendingCount === 1 ? '' : 's'} detected — click <span className="text-accent-primary">Open</span> on any of them, then hit <span className="text-accent-primary">Optimize</span> for a full multi-language deep analysis.
              </p>
            )}
          </div>

          {/* Files table */}
          <div className="bg-ui-panels border border-border-color rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-border-color flex-wrap gap-2">
              <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Per-file Breakdown</h2>
              <div className="flex items-center gap-2 text-xs">
                <span className="text-text-secondary">Sort:</span>
                {(['score', 'violations', 'path'] as const).map((k) => (
                  <button
                    key={k}
                    onClick={() => setSortKey(k)}
                    className={`px-2 py-1 rounded-md border ${sortKey === k ? 'border-accent-primary/50 text-accent-primary bg-accent-primary/10' : 'border-border-color text-text-secondary hover:text-text-primary'}`}
                  >
                    {k === 'score' ? 'Lowest score' : k === 'violations' ? 'Most violations' : 'Name'}
                  </button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-text-secondary border-b border-border-color">
                    <th className="px-4 py-2 font-semibold">File</th>
                    <th className="px-4 py-2 font-semibold">Lang</th>
                    <th className="px-4 py-2 font-semibold">Score</th>
                    <th className="px-4 py-2 font-semibold">Time</th>
                    <th className="px-4 py-2 font-semibold">Space</th>
                    <th className="px-4 py-2 font-semibold">SOLID</th>
                    <th className="px-4 py-2 font-semibold">Clean</th>
                    <th className="px-4 py-2 font-semibold"></th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map((f) => {
                    const clean = f.analysis?.clean_report || {};
                    const analyzed = f.score !== null;
                    const barStyle = { width: `${analyzed ? f.score : 0}%` };
                    return (
                      <tr key={f.path} className="border-b border-border-color/60 hover:bg-accent-primary/5">
                        <td className="px-4 py-2 font-mono text-xs text-text-primary max-w-[240px] truncate" title={f.path}>{f.path}</td>
                        <td className="px-4 py-2"><LangBadge lang={f.language} /></td>
                        <td className="px-4 py-2">
                          {analyzed ? (
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 rounded-full bg-text-secondary/20 overflow-hidden">
                                <div className={`h-full ${scoreBar(f.score as number)}`} style={barStyle} />
                              </div>
                              <span className={`font-mono font-bold ${scoreColor(f.score as number)}`}>{f.score}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-text-secondary italic">{f.error ? f.error : 'Deep analysis pending'}</span>
                          )}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs">{analyzed ? (f.analysis?.time_complexity || '—') : '—'}</td>
                        <td className="px-4 py-2 font-mono text-xs">{analyzed ? (f.analysis?.space_complexity || '—') : '—'}</td>
                        <td className={`px-4 py-2 font-bold text-xs ${analyzed ? (f.violations === 0 ? 'text-green-400' : 'text-red-400') : 'text-text-secondary'}`}>{analyzed ? (f.violations === 0 ? 'Pass' : `${f.violations}`) : '—'}</td>
                        <td className="px-4 py-2 font-mono text-xs">{analyzed ? (clean.score ?? '—') : '—'}</td>
                        <td className="px-4 py-2 text-right">
                          <button onClick={() => openFile(f.path)} disabled={opening === f.path} className="text-xs font-bold text-accent-primary hover:underline disabled:opacity-40">{opening === f.path ? '…' : (analyzed ? 'Open' : 'Open → Optimize')}</button>
                        </td>
                      </tr>
                    );
                  })}
                  {sortedRows.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-text-secondary text-sm">No analyzable code files found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {files.some((f) => f.error) && (
              <div className="px-5 py-3 border-t border-border-color text-xs text-text-secondary">
                {files.filter((f) => f.error).length} file(s) could not be fetched or analyzed.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default RepoAnalysis;
