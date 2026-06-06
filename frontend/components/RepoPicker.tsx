import React, { useEffect, useState } from 'react';

interface Repo {
  name: string;
  full_name: string;
  owner: string;
  private: boolean;
  default_branch: string;
}

interface FileEntry {
  path: string;
  type: string;
}

interface RepoPickerProps {
  token: string;
  onClose: () => void;
  onSelectFile: (content: string, path: string) => void;
}

const API = 'http://localhost:8000';

// File extensions we surface first (analysis is Python-focused).
const CODE_EXTS = ['.py', '.pyw'];

const RepoPicker: React.FC<RepoPickerProps> = ({ token, onClose, onSelectFile }) => {
  const [repos, setRepos]               = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [files, setFiles]               = useState<FileEntry[]>([]);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState('');
  const [search, setSearch]             = useState('');
  const [onlyPython, setOnlyPython]     = useState(true);

  const authHeaders = { Authorization: `Bearer ${token}` };

  // ── Load repos on mount ───────────────────────────────────
  useEffect(() => {
    setLoading(true);
    setError('');
    fetch(`${API}/github/repos`, { headers: authHeaders })
      .then((r) => {
        if (!r.ok) throw new Error('Could not load your repositories. Try signing in again.');
        return r.json();
      })
      .then((data: Repo[]) => setRepos(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Open a repo (load its file tree) ──────────────────────
  const openRepo = (repo: Repo) => {
    setSelectedRepo(repo);
    setFiles([]);
    setSearch('');
    setLoading(true);
    setError('');
    fetch(
      `${API}/github/tree?owner=${encodeURIComponent(repo.owner)}&repo=${encodeURIComponent(repo.name)}`,
      { headers: authHeaders },
    )
      .then((r) => {
        if (!r.ok) throw new Error('Could not load files for this repository.');
        return r.json();
      })
      .then((d: { files: FileEntry[] }) => setFiles(d.files || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  // ── Pick a file (load content into the editor) ────────────
  const pickFile = (file: FileEntry) => {
    if (!selectedRepo) return;
    setLoading(true);
    setError('');
    fetch(
      `${API}/github/file?owner=${encodeURIComponent(selectedRepo.owner)}` +
        `&repo=${encodeURIComponent(selectedRepo.name)}&path=${encodeURIComponent(file.path)}`,
      { headers: authHeaders },
    )
      .then((r) => {
        if (!r.ok) throw new Error('Could not load this file.');
        return r.json();
      })
      .then((d: { content: string }) => {
        onSelectFile(d.content ?? '', file.path);
        onClose();
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const isPython = (p: string) => CODE_EXTS.some((ext) => p.toLowerCase().endsWith(ext));

  const visibleFiles = files
    .filter((f) => (onlyPython ? isPython(f.path) : true))
    .filter((f) => f.path.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => a.path.localeCompare(b.path));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col bg-ui-panels border border-border-color
                   rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-color">
          <div className="flex items-center gap-3 min-w-0">
            {selectedRepo && (
              <button
                onClick={() => { setSelectedRepo(null); setFiles([]); setError(''); setSearch(''); }}
                className="text-text-secondary hover:text-text-primary transition-colors shrink-0"
                title="Back to repositories"
              >
                ←
              </button>
            )}
            <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current text-text-primary shrink-0" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
            </svg>
            <h2 className="text-base font-bold text-text-primary truncate">
              {selectedRepo ? selectedRepo.full_name : 'Import from GitHub'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors text-xl leading-none"
            title="Close"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-grow overflow-y-auto">
          {error && (
            <div className="m-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center py-16">
              <div className="w-10 h-10 border-4 border-accent-primary/20 border-t-accent-primary rounded-full animate-spin" />
            </div>
          )}

          {/* Repo list */}
          {!loading && !selectedRepo && (
            <ul className="divide-y divide-border-color">
              {repos.length === 0 && !error && (
                <li className="px-5 py-8 text-center text-sm text-text-secondary">No repositories found.</li>
              )}
              {repos.map((repo) => (
                <li key={repo.full_name}>
                  <button
                    onClick={() => openRepo(repo)}
                    className="w-full text-left px-5 py-3 flex items-center justify-between
                               hover:bg-accent-primary/5 transition-colors"
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <span className="text-sm font-medium text-text-primary truncate">{repo.name}</span>
                      {repo.private && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded
                                         border border-border-color text-text-secondary shrink-0">
                          Private
                        </span>
                      )}
                    </span>
                    <span className="text-text-secondary text-xs shrink-0">→</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* File list */}
          {!loading && selectedRepo && (
            <div className="flex flex-col">
              <div className="flex items-center gap-3 px-5 py-3 border-b border-border-color sticky top-0 bg-ui-panels">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search files…"
                  className="flex-grow bg-background border border-border-color rounded-lg px-3 py-1.5
                             text-sm text-text-primary outline-none focus:border-accent-primary/50"
                />
                <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={onlyPython}
                    onChange={(e) => setOnlyPython(e.target.checked)}
                  />
                  .py only
                </label>
              </div>
              <ul className="divide-y divide-border-color">
                {visibleFiles.length === 0 && (
                  <li className="px-5 py-8 text-center text-sm text-text-secondary">
                    No matching files.
                  </li>
                )}
                {visibleFiles.map((file) => (
                  <li key={file.path}>
                    <button
                      onClick={() => pickFile(file)}
                      className="w-full text-left px-5 py-2.5 flex items-center gap-2
                                 hover:bg-accent-primary/5 transition-colors font-mono text-xs text-text-primary"
                    >
                      <span className="text-text-secondary">□</span>
                      <span className="truncate">{file.path}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="px-5 py-3 border-t border-border-color text-xs text-text-secondary">
          {selectedRepo
            ? 'Pick a file to load it into the editor.'
            : 'Select a repository to browse its files.'}
        </div>
      </div>
    </div>
  );
};

export default RepoPicker;
