import React, { useState, useCallback, useEffect, useRef } from 'react';
import debounce from 'lodash/debounce';
import { Page } from './types';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import About from './components/About';
import Help from './components/Help';
import Results from './components/Results';
import TimeComplexityReport from './components/TimeComplexityReport';
import SolidReport from './components/SolidReport';
import SpaceComplexityReport from './components/SpaceComplexityReport';
import CleanCodeReport from './components/CleanCodeReport';
import OptimizeReport from './components/OptimizeReport';
import HistorySidebar from './components/HistorySidebar';
import LoginPage from './components/LoginPage';
import RepoAnalysis from './components/RepoAnalysis';
import Trends from './components/Trends';

const App: React.FC = () => {
  const [currentPage, setCurrentPage]     = useState<Page>(
    () => (localStorage.getItem('owlint_token') ? Page.DASHBOARD : Page.LOGIN)
  );
  const [code, setCode]                   = useState<string>('class User:\n    def save(self):\n        pass');
  const [language, setLanguage]           = useState<'python' | 'java'>('python');
  const [selectedModel, setSelectedModel] = useState<string>('openai/gpt-oss-120b');
  const [historyOpen, setHistoryOpen]     = useState(false);
  const [isOptimizing, setIsOptimizing]   = useState(false);
  const [solidLoading, setSolidLoading]   = useState(false);
  const [token, setToken]                 = useState<string | null>(
    () => localStorage.getItem('owlint_token')
  );
  const [githubConnected, setGithubConnected] = useState<boolean>(false);

  const [analysisResult, setAnalysisResult] = useState<any>({
    time_complexity:   'O(1)',
    space_complexity:  'O(1)',
    solid_status:      'Pass',
    clean_code_status: 'Pending',
    solid_report:      { S: { status: 'Pass', reason: 'Ready', suggestion: 'N/A' } },
    total_violations:  0,
    clean_report: {
      score: 0,
      grade: 'N/A',
      passed: false,
      issues: [],
      metrics: { maintainability_index: 0, loc: 0, lloc: 0, comments: 0, cc_max: 0 },
      pylint: [],
    },
    agent_report:      '',
    validator_verdict: '',
    refactored_code:   '',
    suggestions:       [],
  });

  const socketRef        = useRef<WebSocket | null>(null);
  const wsTokenRef       = useRef<string | null>(null);
  const codeRef          = useRef(code);
  const selectedModelRef = useRef(selectedModel);

  useEffect(() => { codeRef.current = code; }, [code]);
  useEffect(() => { selectedModelRef.current = selectedModel; }, [selectedModel]);

  // ── Auth callback ─────────────────────────────────────────
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get('token');
    if (t) {
      localStorage.setItem('owlint_token', t);
      setToken(t);
      window.history.replaceState({}, '', '/');
      setCurrentPage(Page.DASHBOARD);
    }
  }, []);

  // ── Know whether the logged-in user has GitHub linked ─────
  // Google users start without GitHub and unlock repo features by pressing
  // "Connect to GitHub". GitHub users are connected from the start.
  useEffect(() => {
    if (!token) { setGithubConnected(false); return; }
    fetch('http://localhost:8000/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => (r.ok ? r.json() : null))
      .then(u => setGithubConnected(!!u?.github_connected))
      .catch(() => setGithubConnected(false));
  }, [token]);

  // ── Persistent WebSocket ──────────────────────────────────
  const connectWebSocket = useCallback((tok: string | null) => {
  // 1. Keep the current socket ONLY if it's open AND already authenticated with
  //    the same token. Otherwise we must reconnect so the server learns the
  //    user's identity (required to save history). This matters right after
  //    sign-in, when an anonymous socket opened before the token arrived.
  if (
    socketRef.current &&
    socketRef.current.readyState === WebSocket.OPEN &&
    wsTokenRef.current === tok
  ) {
    return;
  }

  // 2. Clear listeners and close any existing socket (wrong token / stale state)
  if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
    socketRef.current.onclose = null;
    socketRef.current.close();
  }

  // Remember which token THIS socket is being opened with.
  wsTokenRef.current = tok;

    const wsUrl = tok
      ? `ws://localhost:8000/ws/analyze?token=${tok}`
      : 'ws://localhost:8000/ws/analyze';

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log('WebSocket connected');

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || data.error) return;
        // MERGE, never replace: typing updates complexity/clean, the Alt+Enter
        // SOLID response updates only SOLID, and neither clobbers the other.
        setAnalysisResult((prev: any) => ({ ...prev, ...data }));
        if (data.refactored_code || data.agent_report || data.validator_verdict) {
          setIsOptimizing(false);
        }
        // SOLID-on-demand response arrived (architect opinion or error).
        if (data.solid_source === 'architect' || data.solid_error) {
          setSolidLoading(false);
        }
      } catch (e) {
        console.error('WebSocket parse error:', e);
        setIsOptimizing(false);
        setSolidLoading(false);
      }
    };

    ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      setIsOptimizing(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed, reconnecting...');
      setTimeout(() => connectWebSocket(tok), 2000);
    };

    socketRef.current = ws;
  }, []);

  useEffect(() => { connectWebSocket(token); }, [token]);

  // ── Debounced typing send ─────────────────────────────────
  const debouncedSend = useCallback(
    debounce((c: string) => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ code: c, trigger: 'typing' }));
      }
    }, 500), []
  );

  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
    debouncedSend(newCode);
  };

  // ── SOLID on demand (Alt+Enter in the editor) ─────────────
  // SOLID is an LLM call (the Architect's opinion), so it only runs when the
  // user explicitly asks for it — not on every keystroke like the static cards.
  const requestSolidAnalysis = useCallback(() => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    setSolidLoading(true);
    ws.send(JSON.stringify({ code: codeRef.current, trigger: 'solid' }));
  }, []);

  const navigateTo = useCallback((page: Page) => setCurrentPage(page), []);

  // ── Optimize ──────────────────────────────────────────────
  const handleAnalyze = useCallback(() => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      alert('Connection not ready, please wait a moment and try again.');
      return;
    }
    setIsOptimizing(true);
    ws.send(JSON.stringify({
      code: codeRef.current,
      trigger: 'analyze',
      model: selectedModelRef.current,
    }));
    navigateTo(Page.OPTIMIZE_REPORT);
  }, [navigateTo]);

  // ── Load history entry ────────────────────────────────────
  const handleLoadHistoryEntry = (entry: any) => {
    setCode(entry.original_code);
    setAnalysisResult({
      ...entry.analysis_report,
      refactored_code: entry.refactored_code,
      suggestions:     entry.suggestions,
      validator_verdict: entry.verdict,
    });
    navigateTo(Page.OPTIMIZE_REPORT);
  };

  const handleOpenInEditor = (content: string) => {
    setCode(content);
    debouncedSend(content);
    navigateTo(Page.DASHBOARD);
  };

  const handleLogout = () => {
    localStorage.removeItem('owlint_token');
    setToken(null);
  };

  // ── Page renderer ─────────────────────────────────────────
  const renderPage = () => {
    switch (currentPage) {

      case Page.LOGIN:
        return <LoginPage onNavigate={navigateTo} />;

      case Page.DASHBOARD:
        return (
          <Dashboard
            onNavigate={navigateTo}
            code={code}
            token={token}
            githubConnected={githubConnected}
            onCodeChange={handleCodeChange}
            analysisResult={analysisResult}
            language={language}
            setLanguage={setLanguage}
            onAnalyze={handleAnalyze}
            onSolidAnalyze={requestSolidAnalysis}
            solidLoading={solidLoading}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        );

      case Page.RESULTS:
        return (
          <Results
            onNavigate={navigateTo}
            results={analysisResult}
            code={code}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            onAnalyze={handleAnalyze}
          />
        );

      case Page.SOLID_REPORT:
        return <SolidReport onNavigate={navigateTo} results={analysisResult} code={code} />;

      case Page.TIME_COMPLEXITY_REPORT:
        return <TimeComplexityReport onNavigate={navigateTo} results={analysisResult} code={code} />;

      case Page.SPACE_COMPLEXITY_REPORT:
        return <SpaceComplexityReport onNavigate={navigateTo} results={analysisResult} code={code} />;

      case Page.CLEAN_CODE_REPORT:
        return <CleanCodeReport onNavigate={navigateTo} results={analysisResult} code={code} />;

      case Page.OPTIMIZE_REPORT:
        return (
          <OptimizeReport
            onNavigate={navigateTo}
            results={analysisResult}
            code={code}
            isLoading={isOptimizing}
          />
        );

      case Page.REPO_ANALYSIS:
        return (
          <RepoAnalysis
            token={token}
            onNavigate={navigateTo}
            onOpenInEditor={handleOpenInEditor}
          />
        );

      case Page.TRENDS:
        return <Trends token={token} onNavigate={navigateTo} />;

      case Page.ABOUT:
        return <About onNavigate={navigateTo} />;

      case Page.HELP:
        return <Help onNavigate={navigateTo} />;

      default:
        return (
          <Dashboard
            onNavigate={navigateTo}
            code={code}
            token={token}
            githubConnected={githubConnected}
            onCodeChange={handleCodeChange}
            analysisResult={analysisResult}
            language={language}
            setLanguage={setLanguage}
            onAnalyze={handleAnalyze}
            onSolidAnalyze={requestSolidAnalysis}
            solidLoading={solidLoading}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        );
    }
  };

  // Don't render Header on login page
  const showHeader = currentPage !== Page.LOGIN;

  return (
    <div className="min-h-screen flex flex-col text-text-primary transition-colors duration-300">
      {showHeader && (
        <Header
          onNavigate={navigateTo}
          onHistoryOpen={() => setHistoryOpen(true)}
          token={token}
          onLogout={handleLogout}
        />
      )}
      <main className="flex-grow flex flex-col container mx-auto px-4 sm:px-6 lg:px-8">
        {renderPage()}
      </main>
      <HistorySidebar
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onLoadEntry={handleLoadHistoryEntry}
        onViewTrends={() => { setHistoryOpen(false); navigateTo(Page.TRENDS); }}
        token={token}
      />
    </div>
  );
};

export default App;
