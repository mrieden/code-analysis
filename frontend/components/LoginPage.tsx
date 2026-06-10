import React, { useState } from 'react';
import { Page } from '../types';
import GradientText from './GradientText';

interface LoginPageProps {
  onNavigate: (page: Page) => void;
}

const FEATURES = [
  { icon: '🧠', title: 'AI Architect',  desc: 'SOLID & clean-code review' },
  { icon: '⚡', title: 'Auto-Refactor', desc: 'Safe, validated rewrites' },
  { icon: '📊', title: 'Deep Metrics',  desc: 'Complexity & quality scores' },
];

const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const [darkMode] = useState(
    () => document.documentElement.classList.contains('dark')
  );

  const handleGitHubLogin = () => {
    window.location.href = 'http://localhost:8000/auth/github/login';
  };

  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:8000/auth/google/login';
  };

  return (
    // No background color here — let the app's background image (set on <body>) show through.
    <div className="relative min-h-screen flex items-center justify-center px-4 py-10">

      <div className="relative w-full max-w-md">

        {/* Card — solid panel color, same as the rest of the app's boxes */}
        <div className="bg-ui-panels border border-border-color rounded-3xl p-8 shadow-2xl">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="relative mb-3">
              <div className="absolute inset-0 bg-accent-primary/30 blur-2xl rounded-full" />
              <img
                src={darkMode ? '/lightlogo.png' : '/darklogo.png'}
                alt="Strivora AI Logo"
                className="relative h-20 w-20"
              />
            </div>
            <GradientText as="h1" className="text-4xl font-bold tracking-wider">
              Strivora AI
            </GradientText>
            <p className="text-text-secondary text-sm mt-2 tracking-widest uppercase">
              See Beyond Syntax
            </p>
          </div>

          {/* Welcome text */}
          <div className="text-center mb-8">
            <h2 className="text-lg font-bold text-text-primary mb-2">Welcome back</h2>
            <p className="text-text-secondary text-sm">
              Sign in to save your history and pick up your code optimizations
              right where you left off.
            </p>
          </div>

          {/* Auth buttons */}
          <div className="space-y-3">

            {/* Google */}
            <button
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-700 font-bold py-3.5 px-6 rounded-xl transition-all border border-gray-300 shadow-lg hover:shadow-xl hover:scale-[1.01] active:scale-[0.99]"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            {/* GitHub */}
            <button
              onClick={handleGitHubLogin}
              className="w-full flex items-center justify-center gap-3 bg-[#24292e] hover:bg-[#2f363d] text-white font-bold py-3.5 px-6 rounded-xl transition-all border border-[#444d56] shadow-lg hover:shadow-xl hover:scale-[1.01] active:scale-[0.99]"
            >
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
              </svg>
              Continue with GitHub
            </button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-border-color" />
            <span className="text-xs text-text-secondary">or</span>
            <div className="flex-1 h-px bg-border-color" />
          </div>

          {/* Continue without login */}
          <button
            onClick={() => onNavigate(Page.DASHBOARD)}
            className="w-full py-3 px-6 rounded-xl border border-border-color text-text-secondary hover:text-text-primary hover:border-accent-primary/40 text-sm font-medium transition-all"
          >
            Continue without signing in
          </button>

          {/* Feature highlights */}
          <div className="grid grid-cols-3 gap-3 mt-8">
            {FEATURES.map(f => (
              <div key={f.title} className="flex flex-col items-center text-center gap-1 p-3 rounded-xl bg-background/40 border border-border-color">
                <span className="text-xl">{f.icon}</span>
                <span className="text-[11px] font-bold text-text-primary leading-tight">{f.title}</span>
                <span className="text-[10px] text-text-secondary leading-tight">{f.desc}</span>
              </div>
            ))}
          </div>

          {/* Note */}
          <p className="text-center text-xs text-text-secondary mt-6">
            Signing in saves your history across sessions.
            Without an account, analysis is still fully functional.
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-text-secondary mt-6">
          Strivora AI — See Beyond Syntax
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
