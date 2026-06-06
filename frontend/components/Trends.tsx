import React, { useEffect, useState } from 'react';
import { Page } from '../types';
import { calculateGlobalScore } from './Results';

interface HistoryEntry {
  entry_id: string;
  created_at: string;
  original_code: string;
  refactored_code: string;
  suggestions: string[];
  verdict: string;
  analysis_report: any;
}

interface TrendsProps {
  token: string | null;
  onNavigate: (page: Page) => void;
}

const API = 'http://localhost:8000';

const scoreColor = (s: number) =>
  s >= 80 ? 'text-green-400' : s >= 50 ? 'text-yellow-400' : 'text-red-400';

const Stat: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <div className="bg-ui-panels border border-border-color rounded-xl p-4 text-center">
    <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
    <p className="text-xs text-text-secondary mt-1">{label}</p>
  </div>
);

const Trends: React.FC<TrendsProps> = ({ token, onNavigate }) => {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError('');
    fetch(`${API}/history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => { if (!r.ok) throw new Error('Could not load history.'); return r.json(); })
      .then((d: HistoryEntry[]) => setEntries(Array.isArray(d) ? d : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  // /history returns newest-first → reverse to chronological order
  const chrono = [...entries].reverse().map((e) => ({
    ...e,
    score: calculateGlobalScore(e.analysis_report),
  }));

  const total      = chrono.length;
  const passCount  = chrono.filter((e) => e.verdict === 'PASS').length;
  const passRate   = total ? Math.round((passCount / total) * 100) : 0;
  const avgScore   = total ? Math.round(chrono.reduce((a, e) => a + e.score, 0) / total) : 0;
  const bestScore  = total ? Math.max(...chrono.map((e) => e.score)) : 0;
  const latest     = total ? chrono[total - 1].score : 0;
  const first      = total ? chrono[0].score : 0;
  const improvement = latest - first;

  const fmt = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  // ── Chart geometry ────────────────────────────────────────
  const W = 640, H = 220, PAD = 32;
  const n = total;
  const px = (i: number) => (n <= 1 ? W / 2 : PAD + (i / (n - 1)) * (W - PAD * 2));
  const py = (s: number) => H - PAD - (s / 100) * (H - PAD * 2);
  const linePoints = chrono.map((e, i) => `${px(i)},${py(e.score)}`).join(' ');
  const areaPoints = n ? `${px(0)},${H - PAD} ${linePoints} ${px(n - 1)},${H - PAD}` : '';

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow py-16 gap-4">
        <p className="text-text-secondary">Sign in to see your trends.</p>
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline">← Back</button>
      </div>
    );
  }

  return (
    <div className="flex flex-col py-6 gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-text-secondary hover:text-text-primary transition-colors">← Back</button>
        <h1 className="text-2xl font-bold text-text-primary">Quality Trends</h1>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><div className="w-10 h-10 border-4 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin" /></div>
      ) : total === 0 ? (
        <div className="text-center py-20">
          <p className="text-5xl mb-3">📈</p>
          <p className="text-text-primary font-bold">No data yet</p>
          <p className="text-text-secondary text-sm mt-1">Optimize some code to start building your trends.</p>
        </div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Stat label="Optimizations" value={`${total}`} color="text-accent-primary" />
            <Stat label="Pass Rate" value={`${passRate}%`} color={passRate >= 70 ? 'text-green-400' : passRate >= 40 ? 'text-yellow-400' : 'text-red-400'} />
            <Stat label="Avg Score" value={`${avgScore}`} color={scoreColor(avgScore)} />
            <Stat label="Best Score" value={`${bestScore}`} color="text-green-400" />
            <Stat label="Net Change" value={`${improvement >= 0 ? '+' : ''}${improvement}`} color={improvement > 0 ? 'text-green-400' : improvement < 0 ? 'text-red-400' : 'text-text-primary'} />
          </div>

          {/* Line chart */}
          <div className="bg-ui-panels border border-border-color rounded-xl p-6">
            <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-4">Score Over Time</h2>
            <div className="w-full overflow-x-auto">
              <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={ { minWidth: 320, maxHeight: 260 } }>
                {/* gridlines */}
                {[0, 25, 50, 75, 100].map((g) => (
                  <g key={g}>
                    <line x1={PAD} y1={py(g)} x2={W - PAD} y2={py(g)} stroke="currentColor" className="text-text-secondary" opacity={0.15} strokeWidth={1} />
                    <text x={6} y={py(g) + 4} fill="currentColor" className="text-text-secondary" opacity={0.7} fontSize={10}>{g}</text>
                  </g>
                ))}
                {n > 1 && <polygon points={areaPoints} fill="currentColor" className="text-accent-primary" opacity={0.12} />}
                {n > 1 && <polyline points={linePoints} fill="none" stroke="currentColor" className="text-accent-primary" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />}
                {chrono.map((e, i) => (
                  <circle key={i} cx={px(i)} cy={py(e.score)} r={3.5} className={e.verdict === 'PASS' ? 'fill-green-400' : 'fill-red-400'} />
                ))}
              </svg>
            </div>
            <div className="flex items-center gap-4 mt-3 text-xs text-text-secondary">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-green-400 inline-block" /> Passed</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" /> Failed</span>
            </div>
          </div>

          {/* Verdict breakdown + recent activity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-ui-panels border border-border-color rounded-xl p-6">
              <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-4">Verdict Breakdown</h2>
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xs text-text-secondary w-12">Passed</span>
                <div className="flex-grow h-3 rounded-full bg-text-secondary/15 overflow-hidden">
                  <div className="h-full bg-green-400" style={{ width: `${passRate}%` }} />
                </div>
                <span className="text-xs font-mono text-text-primary w-10 text-right">{passCount}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-secondary w-12">Failed</span>
                <div className="flex-grow h-3 rounded-full bg-text-secondary/15 overflow-hidden">
                  <div className="h-full bg-red-400" style={{ width: `${100 - passRate}%` }} />
                </div>
                <span className="text-xs font-mono text-text-primary w-10 text-right">{total - passCount}</span>
              </div>
            </div>

            <div className="bg-ui-panels border border-border-color rounded-xl p-6">
              <h2 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-4">Recent Activity</h2>
              <div className="space-y-2">
                {[...chrono].reverse().slice(0, 5).map((e) => (
                  <div key={e.entry_id} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary text-xs">{fmt(e.created_at)}</span>
                    <span className={`font-mono font-bold ${scoreColor(e.score)}`}>{e.score}/100</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${e.verdict === 'PASS' ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>{e.verdict}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Trends;
