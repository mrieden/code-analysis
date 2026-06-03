import React from 'react';
import { Page } from '../types';

interface LoginPageProps {
  onNavigate: (page: Page) => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const handleGitHubLogin = () => {
    window.location.href = 'http://localhost:8000/auth/github/login';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">

        {/* Card */}
        <div className="bg-ui-panels border border-border-color rounded-2xl p-8 shadow-2xl">

          {/* Logo */}
          <div className="text-center mb-8">
            <div className="text-6xl mb-4">🦉</div>
            <h1 className="text-3xl font-bold text-text-primary tracking-tight">
              Owlint
            </h1>
            <p className="text-text-secondary text-sm mt-2 italic">
              See the flaws others miss.
            </p>
          </div>

          {/* Welcome text */}
          <div className="text-center mb-8">
            <h2 className="text-lg font-bold text-text-primary mb-2">Welcome back</h2>
            <p className="text-text-secondary text-sm">
              Sign in to save your analysis history and access your previous code optimizations.
            </p>
          </div>

          {/* GitHub OAuth button */}
          <button
            onClick={handleGitHubLogin}
            className="w-full flex items-center justify-center gap-3
                       bg-[#24292e] hover:bg-[#2f363d] text-white
                       font-bold py-3.5 px-6 rounded-xl transition-all
                       border border-[#444d56] shadow-lg hover:shadow-xl
                       hover:scale-[1.01] active:scale-[0.99]"
          >
            {/* GitHub icon */}
            <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
            </svg>
            Continue with GitHub
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-border-color" />
            <span className="text-xs text-text-secondary">or</span>
            <div className="flex-1 h-px bg-border-color" />
          </div>

          {/* Continue without login */}
          <button
            onClick={() => onNavigate(Page.DASHBOARD)}
            className="w-full py-3 px-6 rounded-xl border border-border-color
                       text-text-secondary hover:text-text-primary hover:border-accent-primary/40
                       text-sm font-medium transition-all"
          >
            Continue without signing in
          </button>

          {/* Note */}
          <p className="text-center text-xs text-text-secondary mt-6">
            Signing in saves your history across sessions.
            Without an account, analysis is still fully functional.
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-text-secondary mt-6">
          Owlint — AI-Powered Code Quality Analysis
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
