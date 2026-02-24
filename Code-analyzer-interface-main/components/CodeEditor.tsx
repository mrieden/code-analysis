import React, { useState, useEffect, useMemo } from 'react';

interface CodeEditorProps {
  // New props for Controlled Mode (State managed by App.tsx)
  value?: string;
  onChange?: (newCode: string) => void;
  language?: string;

  // Legacy/Display props
  initialCode?: string;
  highlightedLines?: number[];
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  value, 
  onChange, 
  initialCode = '', 
  highlightedLines = [], 
  readOnly = false 
}) => {
  // Internal state fallback (if no value prop is provided)
  const [internalCode, setInternalCode] = useState(initialCode);

  // Determine which code source to use (Prop > Internal State)
  const currentCode = value !== undefined ? value : internalCode;

  // Calculate line count based on the current code
  const lineCount = useMemo(() => {
    return currentCode.split('\n').length;
  }, [currentCode]);
  
  const lineNumbers = useMemo(() => {
      return Array.from({ length: lineCount }, (_, i) => i + 1);
  }, [lineCount]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newCode = e.target.value;
    
    // 1. If an external handler exists (from App.tsx), call it
    if (onChange) {
      onChange(newCode);
    }
    
    // 2. If valid, update internal state as well (for uncontrolled usage)
    if (!readOnly && value === undefined) {
      setInternalCode(newCode);
    }
  };

  return (
    <div className="flex bg-ui-panels rounded-lg border border-border-color font-mono text-sm h-full w-full overflow-hidden">
      {/* Line Numbers Sidebar */}
      <div className="line-numbers bg-background text-text-secondary p-4 text-right select-none min-w-[3rem] border-r border-border-color">
        {lineNumbers.map((num) => (
          <div key={num} className={`h-[21px] ${highlightedLines.includes(num) ? 'text-accent-primary font-bold' : ''}`}>
            {num}
          </div>
        ))}
      </div>

      {/* Main Editor Area */}
      <textarea
        value={currentCode}
        onChange={handleChange}
        readOnly={readOnly}
        spellCheck="false"
        className="flex-grow p-4 bg-ui-panels text-text-primary outline-none resize-none leading-[21px] w-full font-mono"
        placeholder="Type your code here..."
      />
    </div>
  );
};

export default CodeEditor;