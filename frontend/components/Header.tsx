import React, { useState } from 'react';
import { Page } from '../types';
import GradientText from './GradientText';

interface HeaderProps {
  onNavigate: (page: Page) => void;
  onHistoryOpen: () => void;
  token: string | null;
  onLogout: () => void;
}

const Header: React.FC<HeaderProps> = ({ onNavigate, onHistoryOpen, token, onLogout }) => {
  const [darkMode, setDarkMode] = useState(
    () => document.documentElement.classList.contains('dark')
  );
  const [showUserMenu, setShowUserMenu] = useState(false);

  const toggleDark = () => {
    document.documentElement.classList.toggle('dark');
    setDarkMode(prev => !prev);
  };

  return (
    <header className="border-b border-border-color bg-ui-panels/80 backdrop-blur-sm sticky top-0 z-30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">

        {/* Logo + Project Name */}
<button
  onClick={() => onNavigate(Page.DASHBOARD)}
  className="flex items-center gap-2 hover:opacity-80 transition-opacity"
>
  <img
    src="/logo.png"
    alt="Strivora AI Logo"
    className="h-20 w-20 mr-2"   // ⬅️ restored to old size
  />
  <div className="flex flex-col items-start">
    <GradientText as="h1" className="text-2xl font-bold tracking-wider">
      Strivora AI
    </GradientText>
    <p className="text-sm text-text-secondary tracking-widest">
      See Beyond Syntax
    </p>
  </div>
</button>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1">
          {[
            { label: 'Dashboard', page: Page.DASHBOARD },
            { label: 'About',     page: Page.ABOUT },
            { label: 'Help',      page: Page.HELP },
          ].map(({ label, page }) => (
            <button
              key={label}
              onClick={() => onNavigate(page)}
              className="px-3 py-1.5 rounded-lg text-sm text-text-secondary
                         hover:text-text-primary hover:bg-accent-primary/10 transition-all"
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Right side controls */}
        <div className="flex items-center gap-2">
          {token && (
            <button
              onClick={onHistoryOpen}
              title="History"
              className="p-2 rounded-lg text-text-secondary hover:text-text-primary
                         hover:bg-accent-primary/10 transition-all"
            >
              {/* Clock icon */}
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none"
                   viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          )}

          {/* Dark mode toggle */}
          <button
            onClick={toggleDark}
            title="Toggle dark mode"
            className="p-2 rounded-lg text-text-secondary hover:text-text-primary
                       hover:bg-accent-primary/10 transition-all"
          >
            {darkMode ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none"
                   viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 7a5 5 0 100 10A5 5 0 0012 7z"/>
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none"
                   viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
              </svg>
            )}
          </button>

          {/* Auth */}
          {token ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(prev => !prev)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                           bg-accent-primary/10 border border-accent-primary/20
                           text-accent-primary text-sm font-bold hover:bg-accent-primary/20 transition-all"
              >
                <span className="text-base">👤</span>
                Account
              </button>
              {showUserMenu && (
                <div className="absolute right-0 top-10 w-40 bg-ui-panels border border-border-color
                                rounded-xl shadow-xl z-50 overflow-hidden">
                  <button
                    onClick={() => { onLogout(); setShowUserMenu(false); }}
                    className="w-full text-left px-4 py-3 text-sm text-red-400
                               hover:bg-red-500/10 transition-all"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => onNavigate(Page.LOGIN)}
              className="px-4 py-1.5 rounded-lg bg-accent-primary text-white
                         text-sm font-bold hover:opacity-90 transition-all shadow-sm"
            >
              Sign in
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
