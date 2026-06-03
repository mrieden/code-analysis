
import React from 'react';
import { Page } from '../types';
import GradientText from './GradientText';

interface AboutProps {
  onNavigate: (page: Page) => void;
}

const About: React.FC<AboutProps> = ({ onNavigate }) => {
  return (
    <div className="max-w-4xl mx-auto py-8 flex-grow">
      <button onClick={() => onNavigate(Page.DASHBOARD)} className="text-accent-primary hover:underline mb-8">
          &larr; Back to Dashboard
      </button>

      <GradientText as="h1" className="text-5xl font-bold text-center mb-4">
        Smarter Code, Not Harder Code.
      </GradientText>
      <p className="text-xl text-center text-text-secondary mb-12">
        Code Analyzer is a graduation project designed to bring intelligent, automated code review to every developer's fingertips.
      </p>

      <div className="space-y-10">
        <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
          <h2 className="text-2xl font-bold text-text-primary mb-3">Core Features</h2>
          <ul className="list-disc list-inside text-text-secondary space-y-2">
            <li><strong className="text-text-primary">Complexity Analysis:</strong> Instantly identify performance hotspots with Big O notation analysis.</li>
            <li><strong className="text-text-primary">SOLID Validation:</strong> Ensure your object-oriented design is robust and maintainable.</li>
            <li><strong className="text-text-primary">Clean Code Checks:</strong> Get suggestions for improving readability and reducing code smells.</li>
            <li><strong className="text-text-primary">Developer-First UX:</strong> A beautiful, futuristic interface designed to reduce eye strain and improve focus.</li>
          </ul>
        </div>

        <div className="bg-ui-panels p-6 rounded-lg border border-border-color">
          <h2 className="text-2xl font-bold text-text-primary mb-3">The Technology Stack</h2>
           <div className="flex flex-wrap gap-4">
                <span className="bg-background px-3 py-1 rounded-full text-accent-primary">React</span>
                <span className="bg-background px-3 py-1 rounded-full text-accent-primary">TypeScript</span>
                <span className="bg-background px-3 py-1 rounded-full text-accent-primary">Tailwind CSS</span>
                <span className="bg-background px-3 py-1 rounded-full text-text-secondary">[Backend Placeholder]</span>
                <span className="bg-background px-3 py-1 rounded-full text-text-secondary">[AI Model Placeholder]</span>
           </div>
        </div>
      </div>
    </div>
  );
};

export default About;