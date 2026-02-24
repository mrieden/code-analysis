import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';
import ComplexityGraph from './ComplexityGraph';

// Define the Analysis Result shape (matching the updated App.tsx)
interface AnalysisResult {
    time_complexity: string;
    space_complexity: string;
    solid_status: string;
    clean_code_status: string;
    // ✅ ADDED: Hotspot fields for Time Complexity
    time_hotspot_line: number;
    time_hotspot_snippet: string;
    // Added for completeness, matching the full interface
    space_hotspot_line: number;
    space_hotspot_variable: string;
}

interface TimeComplexityReportProps {
    onNavigate: (page: Page) => void;
    results: AnalysisResult;
    code: string;
}

const TimeComplexityReport: React.FC<TimeComplexityReportProps> = ({ onNavigate, results, code }) => {

    // Get the actual complexity result and the new hotspot data
    const timeComplexity = results.time_complexity;
    const hotspotLine = results.time_hotspot_line; // ✅ Use dynamic line
    const hotspotSnippet = results.time_hotspot_snippet; // ✅ Use dynamic snippet

    // Logic to determine status text and color
    const getStatus = (val: string) => {
        if (val.includes('1') || val.includes('log')) return { text: "Excellent", color: "text-status-success" };
        if (val.includes('n^2') || val.includes('^3') || val.includes('2^n')) return { text: "Poor", color: "text-status-error" };
        if (val === "O(n)") return { text: "Good", color: "text-accent-secondary" };
        return { text: "Review", color: "text-status-warning" };
    };

    const statusObj = getStatus(timeComplexity);

    // Simple dynamic advice based on complexity
    const getAdvice = (val: string) => {
        if (val === "O(1)") return "Your code uses constant time and is highly efficient.";
        if (val === "O(n)") return "The algorithm scales linearly. This is generally good, but check for potential O(1) opportunities.";
        if (val.includes('n^2') || val.includes('^3')) return "Quadratic or Cubic complexity detected. This will be very slow for large datasets and requires optimization.";
        if (val.includes('2^n')) return "Exponential complexity detected, which is extremely inefficient. Consider memoization or dynamic programming.";
        return "Complexity analysis complete. Review the code to ensure the performance meets requirements.";
    };

    return (
        <div className="flex flex-col gap-8 flex-grow py-8">
            <div>
                <button onClick={() => onNavigate(Page.RESULTS)} className="text-accent-primary hover:underline mb-4">
                    &larr; Back to Summary
                </button>
                <GradientText as="h1" className="text-4xl font-bold">Detailed Report: Time Complexity</GradientText>
            </div>

            <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
                <h2 className="text-2xl font-bold text-text-primary mb-2">
                    Overall Time Complexity: <span className={`font-mono ${statusObj.color}`}>{timeComplexity}</span>
                </h2>
                <p className="text-lg mb-2">
                    <span className="font-semibold">Status:</span>
                    <span className={`ml-2 font-bold ${statusObj.color}`}>{statusObj.text}</span>
                </p>
                <p className="text-text-secondary">{getAdvice(timeComplexity)}</p>
            </div>

            {/* Code Hotspots: Now displays the user's code */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="flex flex-col gap-4">
                    <h3 className="text-xl font-semibold">Code Snippet</h3>
                    <div className="h-80">
                        {/* ✅ CHANGED: Use dynamic hotspotLine */}
                        <CodeEditor value={code} highlightedLines={[hotspotLine]} readOnly={true} />
                    </div>
                </div>
                <div className="flex flex-col gap-4">
                    <h3 className="text-xl font-semibold">Performance Insights</h3>
                    <div className="bg-ui-panels p-4 rounded-lg border border-border-color">
                        {/* ✅ CHANGED: Use dynamic hotspot data */}
                        <p className="text-text-secondary">
                            Line **{hotspotLine}** (`{hotspotSnippet}`) is the primary contributor to the **{timeComplexity}** complexity because it determines the rate of execution time growth relative to the input data size.
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
                <h2 className="text-2xl font-bold text-text-primary mb-4">Growth Rate Visualization</h2>
                <div className="flex flex-col md:flex-row gap-6">
                    <p className="md:w-1/2 text-text-secondary">
                        Big O notation classifies algorithms by how their run time grows as the input size grows. The graph illustrates how quickly your calculated complexity ({timeComplexity}) scales compared to ideal (O(1)) and inefficient (O(n²)) curves.
                    </p>
                    <div className="md:w-1/2 min-h-[16rem] bg-background rounded-lg border border-border-color flex items-center justify-center p-4">
                        <ComplexityGraph />
                    </div>
                </div>
            </div>

            <div className="flex justify-end mt-4">
                <button
                    onClick={() => onNavigate(Page.SPACE_COMPLEXITY_REPORT)}
                    className="bg-accent-secondary text-white font-semibold px-6 py-3 rounded-lg hover:opacity-90 transition-all shadow-md">
                    Next: Space Complexity Report &rarr;
                </button>
            </div>

        </div>
    );
};

export default TimeComplexityReport;