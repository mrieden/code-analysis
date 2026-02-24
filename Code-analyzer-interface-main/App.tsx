import React, { useState, useCallback, useEffect, useRef } from 'react';
import debounce from 'lodash/debounce';
import { Page } from './types';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import About from './components/About';
import Help from './components/Help';
import Results from './components/Results'; // EXACT NAME FIXED
import TimeComplexityReport from './components/TimeComplexityReport';
import SolidReport from './components/SolidReport';
import SpaceComplexityReport from './components/SpaceComplexityReport';
import CleanCodeReport from './components/CleanCodeReport';
import OptimizeReport from './components/OptimizeReport';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>(Page.DASHBOARD);
  const [code, setCode] = useState<string>('class User:\n    def save(self):\n        pass');
  const [language, setLanguage] = useState<'python' | 'java'>('python');

  const [analysisResult, setAnalysisResult] = useState<any>({
    time_complexity: 'O(1)',
    space_complexity: 'O(1)',
    solid_status: 'Pass',
    clean_code_status: 'Pending',
    solid_report: { S: { status: 'Pass', reason: 'Ready', suggestion: 'N/A' } }
  });

  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/analyze');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && !data.error) setAnalysisResult(data);
      } catch (e) { console.error(e); }
    };
    socketRef.current = ws;
    return () => { if(ws.readyState === 1) ws.close(); };
  }, []);

  const debouncedSend = useCallback(
    debounce((c: string) => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ code: c }));
      }
    }, 500), []
  );

  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
    debouncedSend(newCode);
  };

  const navigateTo = useCallback((page: Page) => {
    setCurrentPage(page);
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case Page.DASHBOARD:
        return <Dashboard 
                  onNavigate={navigateTo} 
                  code={code} 
                  onCodeChange={handleCodeChange} 
                  analysisResult={analysisResult}
                  language={language}
                  setLanguage={setLanguage}
                />;

      // --- THE HUB ---
      case Page.RESULTS:
        return <Results onNavigate={navigateTo} results={analysisResult} code={code} />;

      // --- SPECIFIC REPORTS ---
      case Page.SOLID_REPORT:
        return <SolidReport onNavigate={navigateTo} results={analysisResult} code={code} />;
      case Page.TIME_COMPLEXITY_REPORT:
        return <TimeComplexityReport onNavigate={navigateTo} results={analysisResult} code={code} />;
      case Page.SPACE_COMPLEXITY_REPORT:
        return <SpaceComplexityReport onNavigate={navigateTo} results={analysisResult} code={code} />;
      
      case Page.ABOUT:
        return <About onNavigate={navigateTo} />;
      case Page.HELP:
        return <Help onNavigate={navigateTo} />;
      case Page.CLEAN_CODE_REPORT:
        return <CleanCodeReport onNavigate={navigateTo} results={analysisResult} code={code} />;
      case Page.OPTIMIZE_REPORT:
        return <OptimizeReport onNavigate={navigateTo} results={analysisResult} code={code} />;
      
      default:
        return <Dashboard 
                  onNavigate={navigateTo} 
                  code={code} 
                  onCodeChange={handleCodeChange} 
                  analysisResult={analysisResult}
                  language={language}
                  setLanguage={setLanguage}
                />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col text-text-primary transition-colors duration-300">
      <Header onNavigate={navigateTo} />
      <main className="flex-grow flex flex-col container mx-auto px-4 sm:px-6 lg:px-8">
        {renderPage()}
      </main>
    </div>
  );
};

export default App;