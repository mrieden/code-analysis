import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor'; // Ensure this component accepts 'value' and 'onChange' props

// 1. Define the Analysis Result shape (matching App.tsx)
interface AnalysisResult {
    time_complexity: string;
    space_complexity: string;
    solid_status: string;
    clean_code_status: string;
}

// 2. Update Props to accept State & Handlers from App.tsx
interface DashboardProps {
    onNavigate: (page: Page) => void;
    code: string;
    onCodeChange: (newCode: string) => void;
    analysisResult: AnalysisResult;
    language: 'python' | 'java';
    setLanguage: (lang: 'python' | 'java') => void;
}

const Dashboard: React.FC<DashboardProps> = ({ 
    onNavigate, 
    code, 
    onCodeChange, 
    analysisResult, 
    language, 
    setLanguage 
}) => {
    
    // Helper to determine color based on complexity (optional visual flair)
    const getTimeColor = (complexity: string) => {
        if (complexity.includes('1') || complexity.includes('log')) return 'text-accent-secondary'; // Green-ish/Good
        if (complexity.includes('n^2') || complexity.includes('!')) return 'text-status-error'; // Red/Bad
        return 'text-accent-primary'; // Neutral/Linear
    };

    return (
        <div className="flex flex-col flex-grow py-6 gap-6 h-full">

            {/* Top Section: Editor + Complexity Windows */}
            <div className="flex flex-col lg:flex-row gap-6 flex-grow min-h-0">

                {/* Left: Input Window */}
                <div className="lg:w-2/3 flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold text-text-primary">Input Code</h2>
                        
                        {/* CONTROLLED LANGUAGE SELECTOR */}
                        <select 
                            value={language}
                            onChange={(e) => setLanguage(e.target.value as 'python' | 'java')}
                            className="bg-ui-panels border border-border-color rounded-md px-3 py-1 outline-none focus:ring-2 focus:ring-accent-primary text-sm text-text-primary"
                        >
                            <option value="python">Python</option>
                            <option value="java">Java</option>
                            {/* Add C++ or JS if supported in backend later */}
                        </select>
                    </div>

                    <div className="flex-grow border border-border-color rounded-lg overflow-hidden shadow-sm h-[500px] lg:h-auto">
                        {/* CONTROLLED CODE EDITOR 
                            Note: You might need to update CodeEditor.tsx to accept 'value' and 'onChange' 
                            instead of 'initialCode' if you haven't already. 
                        */}
                        <CodeEditor 
                            value={code} 
                            onChange={onCodeChange} 
                            language={language}
                        />
                    </div>
                </div>

                {/* Right: Complexity Windows (REAL-TIME DATA) */}
                <div className="lg:w-1/3 flex flex-col gap-6">

                    {/* Time Complexity Window */}
                    <div className="bg-ui-panels flex-1 rounded-lg border border-border-color p-8 flex flex-col justify-center items-center relative overflow-hidden group shadow-md hover:shadow-lg transition-all">
                        <div className="absolute inset-0 bg-gradient-to-br from-accent-primary/5 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500"></div>
                        <h3 className="text-text-secondary font-semibold uppercase tracking-wider mb-2 z-10 text-sm">Time Complexity</h3>
                        
                        {/* DYNAMIC VALUE */}
                        <p className={`text-6xl font-mono font-bold z-10 drop-shadow-sm transition-all duration-300 ${getTimeColor(analysisResult.time_complexity)}`}>
                            {analysisResult.time_complexity}
                        </p>
                        
                        <div className="mt-4 px-3 py-1 bg-accent-primary/10 rounded-full border border-accent-primary/20 z-10">
                            <span className="text-xs font-bold text-accent-primary">Real-time Analysis</span>
                        </div>
                    </div>

                    {/* Space Complexity Window */}
                    <div className="bg-ui-panels flex-1 rounded-lg border border-border-color p-8 flex flex-col justify-center items-center relative overflow-hidden group shadow-md hover:shadow-lg transition-all">
                        <div className="absolute inset-0 bg-gradient-to-br from-accent-secondary/5 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500"></div>
                        <h3 className="text-text-secondary font-semibold uppercase tracking-wider mb-2 z-10 text-sm">Space Complexity</h3>
                        
                        {/* DYNAMIC VALUE */}
                        <p className="text-6xl font-mono text-accent-secondary font-bold z-10 drop-shadow-sm transition-all duration-300">
                            {analysisResult.space_complexity}
                        </p>
                        
                        <div className="mt-4 px-3 py-1 bg-accent-secondary/10 rounded-full border border-accent-secondary/20 z-10">
                            <span className="text-xs font-bold text-accent-secondary">Real-time Analysis</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom: Check Button */}
            <div className="w-full">
                <button
                    onClick={() => onNavigate(Page.RESULTS)}
                    className="w-full bg-gradient-to-r from-accent-primary to-accent-secondary text-white dark:text-background font-bold text-2xl px-8 py-6 rounded-lg hover:opacity-90 transition-all shadow-lg hover:shadow-xl hover:scale-[1.005] active:scale-[0.99] uppercase tracking-widest flex items-center justify-center gap-3">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Check Code
                </button>
            </div>

        </div>
    );
};

export default Dashboard;