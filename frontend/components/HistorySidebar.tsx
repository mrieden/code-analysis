import React, { useState, useEffect } from 'react';

interface HistoryEntry {
  entry_id: string;
  created_at: string;
  original_code: string;
  refactored_code: string;
  suggestions: string[];
  verdict: string;
  analysis_report: any;
}

interface HistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadEntry: (entry: HistoryEntry) => void;
  onViewTrends: () => void;
  token: string | null;
}

const API = 'http://localhost:8000';

const HistorySidebar: React.FC<HistorySidebarProps> = ({ isOpen, onClose, onLoadEntry, onViewTrends, token }) => {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && token) fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, token]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setEntries(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to fetch history:', e);
    } finally {
      setLoading(false);
    }
  };

  const deleteEntry = async (entryId: string) => {
    setDeletingId(entryId);
    try {
      await fetch(`${API}/history/${entryId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      setEntries((prev) => prev.filter((e) => e.entry_id !== entryId));
    } catch (e) {
      console.error('Failed to delete:', e);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const previewCode = (code: string) =>
    code?.split('\n').slice(0, 2).join('\n') || 'Empty code';

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <div className={`
        fixed top-0 right-0 h-full w-80 z-50
        bg-ui-panels border-l border-border-color
        shadow-2xl flex flex-col
        transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-color">
          <div>
            <h2 className="text-base font-bold text-text-primary">History</h2>
            <p className="text-xs text-text-secondary mt-0.5">{entries.length} saved analyses</p>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* View trends button */}
        {token && entries.length > 0 && (
          <div className="px-3 pt-3">
            <button
              onClick={onViewTrends}
              className="w-full flex items-center justify-center gap-2 text-xs font-bold py-2 rounded-lg
                         bg-accent-primary/10 border border-accent-primary/30 text-accent-primary
                         hover:bg-accent-primary/20 transition-all"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8m0 0h-5m5 0v5" />
              </svg>
              View Trends
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-3 px-3 space-y-2">
          {!token && (
            <div className="text-center py-10">
              <p className="text-text-secondary text-sm">Sign in to see your history</p>
            </div>
          )}

          {token && loading && (
            <div className="text-center py-10">
              <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent
                              rounded-full animate-spin mx-auto mb-2" />
              <p className="text-text-secondary text-sm">Loading...</p>
            </div>
          )}

          {token && !loading && entries.length === 0 && (
            <div className="text-center py-10">
              <p className="text-4xl mb-3">🦉</p>
              <p className="text-text-secondary text-sm">No history yet</p>
              <p className="text-text-secondary text-xs mt-1">
                Optimize some code to see it here
              </p>
            </div>
          )}

          {token && !loading && entries.map((entry) => (
            <div
              key={entry.entry_id}
              className="bg-background border border-border-color rounded-xl p-3
                         hover:border-accent-primary/40 transition-all group"
            >
              {/* Entry header */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-text-secondary">
                  {formatDate(entry.created_at)}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full border
                  ${entry.verdict === 'PASS'
                    ? 'bg-green-500/10 border-green-500/30 text-green-400'
                    : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                  {entry.verdict}
                </span>
              </div>

              {/* Code preview */}
              <pre className="text-xs font-mono text-text-secondary bg-black/20
                              rounded-lg p-2 truncate overflow-hidden max-h-12 mb-3">
                {previewCode(entry.original_code)}
              </pre>

              {/* Suggestions count */}
              {entry.suggestions?.length > 0 && (
                <p className="text-xs text-text-secondary mb-3">
                  {entry.suggestions.length} suggestion{entry.suggestions.length > 1 ? 's' : ''} applied
                </p>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => { onLoadEntry(entry); onClose(); }}
                  className="flex-1 text-xs font-bold py-1.5 rounded-lg
                             bg-accent-primary/10 border border-accent-primary/30
                             text-accent-primary hover:bg-accent-primary/20 transition-all"
                >
                  Open
                </button>
                <button
                  onClick={() => deleteEntry(entry.entry_id)}
                  disabled={deletingId === entry.entry_id}
                  className="text-xs font-bold py-1.5 px-3 rounded-lg
                             bg-red-500/10 border border-red-500/20
                             text-red-400 hover:bg-red-500/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {deletingId === entry.entry_id ? '...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

export default HistorySidebar;
