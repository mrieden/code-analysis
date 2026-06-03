import React from 'react';
import { Page } from '../types';
import CodeEditor from './CodeEditor';
import GradientText from './GradientText';
import ComplexityGraph from './ComplexityGraph';

interface AnalysisResult {
    time_complexity: string;
    space_complexity: string;
    solid_status: string;
    clean_code_status: string;
    time_hotspot_line: number;
    time_hotspot_snippet: string;
    space_hotspot_line: number;
    space_hotspot_variable: string;
}

interface SpaceComplexityReportProps {
    onNavigate: (page: Page) => void;
    results: AnalysisResult;
    code: string;
}

const SpaceComplexityReport: React.FC<SpaceComplexityReportProps> = ({ onNavigate, results, code }) => {

    const spaceComplexity = results.space_complexity;
    const hotspotLine = results.space_hotspot_line;
    const hotspotVariable = results.space_hotspot_variable;

    const getStatus = (val: string) => {
        if (val === "O(1)") return { text: "Excellent", color: "text-status-success" };
        if (val.includes('n^2') || val.includes('2^n')) return { text: "Poor", color: "text-status-error" };
        if (val === "O(n)") return { text: "Good", color: "text-accent-secondary" };
        return { text: "Review", color: "text-status-warning" };
    };

    const statusObj = getStatus(spaceComplexity);

    const getAdvice = (val: string) => {
        if (val === "O(1)") return "Your code uses a constant amount of extra memory, which is highly efficient for any input size.";
        if (val === "O(n)") return "Memory usage grows linearly with the input size. This often means you are creating a new data structure proportional to the input size.";
        if (val.includes('n^2')) return "The algorithm requires memory proportional to the square of the input size. This can quickly lead to memory exhaustion.";
        return "Space complexity analysis complete. Review memory usage for recursive calls or large data structures.";
    };

    return (
        <div className="flex flex-col gap-8 flex-grow py-8">
            <div>
                <button onClick={() => onNavigate(Page.RESULTS)} className="text-accent-primary hover:underline mb-4">
                    &larr; Back to Summary
                </button>
                <GradientText as="h1" className="text-4xl font-bold">Detailed Report: Space Complexity</GradientText>
            </div>

            <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
                <h2 className="text-2xl font-bold text-text-primary mb-2">
                    Overall Space Complexity: <span className={`font-mono ${statusObj.color}`}>{spaceComplexity}</span>
                </h2>
                <p className="text-lg mb-2">
                    <span className="font-semibold">Status:</span>
                    <span className={`ml-2 font-bold ${statusObj.color}`}>{statusObj.text}</span>
                </p>
                <p className="text-text-secondary">{getAdvice(spaceComplexity)}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="flex flex-col gap-4">
                    <h3 className="text-xl font-semibold">Analyzed Code (Memory Usage)</h3>
                    <div className="h-80">
                        <CodeEditor value={code} highlightedLines={[hotspotLine]} readOnly={true} />
                    </div>
                </div>
                <div className="flex flex-col gap-4">
                    <h3 className="text-xl font-semibold">Memory Hotspots</h3>
                    <div className="bg-ui-panels rounded-lg border border-border-color overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-background">
                                <tr>
                                    <th className="p-3">Line #</th>
                                    <th className="p-3">Variable/Structure</th>
                                    <th className="p-3">Complexity</th>
                                    <th className="p-3">Reason</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr className="border-t border-border-color hover:bg-background/50 transition-colors">
                                    <td className="p-3 font-mono text-accent-primary">{hotspotLine}</td>
                                    <td className="p-3 font-mono">{hotspotVariable}</td>
                                    <td className={`p-3 font-mono ${statusObj.color}`}>{spaceComplexity}</td>
                                    <td className="p-3">{getAdvice(spaceComplexity)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
                <h2 className="text-2xl font-bold text-text-primary mb-4">Space vs. Time Tradeoffs</h2>
                <div className="flex flex-col md:flex-row gap-6">
                    <p className="md:w-1/2 text-text-secondary">
                        In algorithm design, there is often a tradeoff between Time and Space complexity.
                        Using more memory for memoization or dynamic programming tables can drastically
                        reduce execution time.
                    </p>
                    <div className="md:w-1/2 min-h-[16rem] bg-background rounded-lg border border-border-color flex items-center justify-center p-4">
                        <ComplexityGraph />
                    </div>
                </div>
            </div>

            <div className="flex justify-between mt-4">
                <button
                    onClick={() => onNavigate(Page.TIME_COMPLEXITY_REPORT)}
                    className="bg-ui-panels text-text-primary font-semibold px-6 py-3 rounded-lg border border-border-color hover:opacity-90 transition-all shadow-md"
                >
                    &larr; Previous: Time Complexity
                </button>
                <button
                    onClick={() => onNavigate(Page.SOLID_REPORT)}
                    className="bg-accent-secondary text-white font-semibold px-6 py-3 rounded-lg hover:opacity-90 transition-all shadow-md"
                >
                    Next: SOLID Report &rarr;
                </button>
            </div>
        </div>
    );
};

export default SpaceComplexityReport;
