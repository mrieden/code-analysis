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

const App: React.FC = () => {
  const [currentPage, setCurrentPage]     = useState<Page>(Page.DASHBOARD);
  const [code, setCode]                   = useState<string>('class User:\n    def save(self):\n        pass');
  const [language, setLanguage]           = useState<'python' | 'java'>('python');
  const [selectedModel, setSelectedModel] = useState<string>('llama-3.1-8b');
  const [historyOpen, setHistoryOpen]     = useState(false);
  const [isOptimizing, setIsOptimizing]   = useState(false);
  const [token, setToken]                 = useState<string | null>(
    () => localStorage.getItem('owlint_token')
  );

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

  // ── Persistent WebSocket ──────────────────────────────────
  const connectWebSocket = useCallback((tok: string | null) => {
  // 1. Don't reconnect if already open
  if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
    return;
  }

  // 2. Clear listeners and close if it exists in any other non-CLOSED state
  if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
    socketRef.current.onclose = null;
    socketRef.current.close();
  }

    const wsUrl = tok
      ? `ws://localhost:8000/ws/analyze?token=${tok}`
      : 'ws://localhost:8000/ws/analyze';

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log('WebSocket connected');

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || data.error) return;
        setAnalysisResult(data);
        if (data.refactored_code || data.agent_report || data.validator_verdict) {
          setIsOptimizing(false);
        }
      } catch (e) {
        console.error('WebSocket parse error:', e);
        setIsOptimizing(false);
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
            onCodeChange={handleCodeChange}
            analysisResult={analysisResult}
            language={language}
            setLanguage={setLanguage}
            onAnalyze={handleAnalyze}
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

      case Page.ABOUT:
        return <About onNavigate={navigateTo} />;

      case Page.HELP:
        return <Help onNavigate={navigateTo} />;

      default:
        return (
          <Dashboard
            onNavigate={navigateTo}
            code={code}
            onCodeChange={handleCodeChange}
            analysisResult={analysisResult}
            language={language}
            setLanguage={setLanguage}
            onAnalyze={handleAnalyze}
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
        token={token}
      />
    </div>
  );
};

export default App;
