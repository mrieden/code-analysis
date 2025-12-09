import React, { useState, useCallback } from 'react';
import { Page } from './types';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import About from './components/About';
import Help from './components/Help';
import TimeComplexityReport from './components/TimeComplexityReport';
import SolidReport from './components/SolidReport';
import SpaceComplexityReport from './components/SpaceComplexityReport';
import CleanCodeReport from './components/CleanCodeReport';
import OptimizeReport from './components/OptimizeReport';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>(Page.DASHBOARD);

  const navigateTo = useCallback((page: Page) => {
    setCurrentPage(page);
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case Page.DASHBOARD:
        return <Dashboard onNavigate={navigateTo} />;
      case Page.ABOUT:
        return <About onNavigate={navigateTo} />;
      case Page.HELP:
        return <Help onNavigate={navigateTo} />;
      case Page.TIME_COMPLEXITY_REPORT:
        return <TimeComplexityReport onNavigate={navigateTo} />;
      case Page.SOLID_REPORT:
        return <SolidReport onNavigate={navigateTo} />;
      case Page.SPACE_COMPLEXITY_REPORT:
        return <SpaceComplexityReport onNavigate={navigateTo} />;
      case Page.CLEAN_CODE_REPORT:
        return <CleanCodeReport onNavigate={navigateTo} />;
      case Page.OPTIMIZE_REPORT:
        return <OptimizeReport onNavigate={navigateTo} />;
      default:
        return <Dashboard onNavigate={navigateTo} />;
    }
  };

  return (
    // REMOVED 'bg-background' so the body image shows through
    <div className="min-h-screen flex flex-col text-text-primary transition-colors duration-300">
      <Header onNavigate={navigateTo} />
      <main className="flex-grow flex flex-col container mx-auto px-4 sm:px-6 lg:px-8">
        {renderPage()}
      </main>
    </div>
  );
};

export default App;
