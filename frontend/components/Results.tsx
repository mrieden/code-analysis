
import React from 'react';
import { Page } from '../types';
import ScoreCircle from './ScoreCircle';

interface ResultsProps {
    onNavigate: (page: Page) => void;
    results: any;
}

const Results: React.FC<ResultsProps> = ({ onNavigate, results: analysisData }) => {
    
    // Helper function to calculate the score based on our brainstorm
    const calculateGlobalScore = () => {
    if (!analysisData || analysisData.error) return 0;

    // 1. Clean Code (40%) - Mapping your naming_score & maintainability
    const clean = analysisData.clean_report || {};
    const namingScore = clean.naming_quality?.naming_score || 0;
    const miScore = clean.radon?.maintainability_index || 0;

    // We give 10 points for Green, 7 for Yellow
    const namingPts = namingScore > 80 ? 10 : namingScore > 50 ? 7 : 0;
    const miPts = miScore > 70 ? 10 : miScore > 40 ? 7 : 0;
    const lintPts = (clean.pylint?.length === 0) ? 10 : 7;
    const densityPts = 10; // Defaulting for now

    const cleanTotal = namingPts + miPts + lintPts + densityPts;

    // 2. SOLID (35%) - Your backend sends S, O, L, I, D keys directly
    const solid = analysisData.solid_report || {};
    const solidScore = ['S', 'O', 'L', 'I', 'D'].reduce((acc, key) => {
        return acc + (solid[key]?.status === 'Pass' ? 7 : 0);
    }, 0);

    // 3. Time Complexity (15%) - Your backend sends "O(N^depth)"
    // If depth is 0 or 1, it's a Pass. If 2+, it's a Warning/Issue.
    const timeValue = analysisData.time_complexity || "O(1)";
    const timeScore = (timeValue === "O(1)" || timeValue === "O(N^1)") ? 15 : 7;

    // 4. Space Complexity (10%) - Your backend currently sends hardcoded "O(1)"
    const spaceScore = analysisData.space_complexity === "O(1)" ? 10 : 7;

    return Math.round(cleanTotal + solidScore + timeScore + spaceScore);
};

    const globalScore = calculateGlobalScore();

    return (
        // ... rest of your code
        <div className="flex flex-col items-center justify-center flex-grow py-8 gap-8 max-w-4xl mx-auto w-full">
            <div className="w-full bg-ui-panels/70 p-8 rounded-lg border border-border-color shadow-2xl shadow-background animate-fade-in-up">
                <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-4 self-start font-medium">
                    &larr; Back to Editor
                </button>

                <div className="flex justify-center mb-10">
    {/* Now the circle will animate to the real calculated value! */}
    <ScoreCircle score={globalScore} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* 1. Time Complexity Card */}
<div onClick={() => onNavigate(Page.TIME_COMPLEXITY_REPORT)} className="bg-ui-panels p-6 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary group">
    <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">Time Complexity</h3>
    <p className={`text-3xl font-mono ${
        // main.py sends 'time_complexity'. We check if it's O(1) or O(N^1)
        (analysisData.time_complexity === 'O(1)' || analysisData.time_complexity === 'O(N^1)') 
        ? 'text-status-success' : 'text-status-warning'
    }`}>
        {analysisData.time_complexity || 'O(1)'}
    </p>
</div>

{/* 2. Space Complexity Card */}
<div onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)} className="bg-ui-panels p-6 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary group">
    <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">Space Complexity</h3>
    <p className={`text-3xl font-mono ${
        analysisData.space_complexity === 'O(1)' ? 'text-status-success' : 'text-status-warning'
    }`}>
        {analysisData.space_complexity || 'O(1)'}
    </p>
</div>

{/* 3. SOLID Principles Card */}
<div onClick={() => onNavigate(Page.SOLID_REPORT)} className="bg-ui-panels p-6 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary group">
    <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">SOLID Principles</h3>
    <p className={`text-xl font-semibold ${analysisData.total_violations === 0 ? 'text-status-success' : 'text-status-error'}`}>
        {analysisData.total_violations === 0 ? "All Pass ✅" : `${analysisData.total_violations} Violations Found`}
    </p>
</div>

{/* 4. Clean Code Card */}
<div onClick={() => onNavigate(Page.CLEAN_CODE_REPORT)} className="bg-ui-panels p-6 rounded-lg border border-border-color transition-all duration-300 ease-in-out hover:-translate-y-1 hover:shadow-lg hover:shadow-accent-secondary/10 cursor-pointer hover:border-accent-primary group">
    <h3 className="font-bold text-lg text-text-primary mb-2 group-hover:text-accent-primary transition-colors">Clean Code</h3>
    <p className={`text-xl font-semibold ${globalScore > 80 ? 'text-status-success' : 'text-status-warning'}`}>
        {globalScore > 90 ? "Excellent ✅" : globalScore > 70 ? "Needs Polish ⚠️" : "Refactor Required ❌"}
    </p>
    <p className="text-sm text-text-secondary">Score: {globalScore}%</p>
</div>
                </div>

                <button
                    onClick={() => onNavigate(Page.OPTIMIZE_REPORT)}
                    className="w-full bg-gradient-to-r from-accent-primary to-accent-secondary text-white dark:text-background font-bold text-xl px-6 py-4 rounded-md hover:opacity-90 transition-opacity shadow-md hover:shadow-lg mt-8 uppercase tracking-wide">
                    Optimize
                </button>
            </div>
        </div>
    );
};

export default Results;