
import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

const complexityColors = {
  dark: {
    nSquared: '#FF4757',
    n: '#00F5D4',
    logN: '#9B5DE5',
    one: '#00FF7F',
  },
  light: {
    nSquared: '#DC2626',
    n: '#00A38E',
    logN: '#864ADF',
    one: '#16A34A',
  }
}

const ComplexityGraph: React.FC = () => {
  const { theme } = useTheme();
  const colors = theme === 'light' ? complexityColors.light : complexityColors.dark;

  return (
    <svg width="100%" height="100%" viewBox="0 0 300 200" className="text-text-secondary">
      {/* Grid lines */}
      <line x1="20" y1="180" x2="280" y2="180" stroke="currentColor" strokeWidth="0.5" />
      <line x1="20" y1="20" x2="20" y2="180" stroke="currentColor" strokeWidth="0.5" />

      {/* Axis Labels */}
      <text x="150" y="195" textAnchor="middle" fontSize="10" fill="currentColor">Input Size (n)</text>
      <text x="10" y="100" writingMode="vertical-rl" textAnchor="middle" fontSize="10" fill="currentColor">Operations</text>

      {/* O(n^2) */}
      <path d="M 20 180 Q 100 170, 200 20" stroke={colors.nSquared} strokeWidth="1.5" fill="none" />
      <text x="205" y="25" fill={colors.nSquared} fontSize="10">O(n²)</text>

      {/* O(n) */}
      <path d="M 20 180 L 250 30" stroke={colors.n} strokeWidth="1.5" fill="none" />
      <text x="255" y="35" fill={colors.n} fontSize="10">O(n)</text>

      {/* O(log n) */}
      <path d="M 20 180 Q 150 160, 270 110" stroke={colors.logN} strokeWidth="1.5" fill="none" />
      <text x="275" y="115" fill={colors.logN} fontSize="10">O(log n)</text>

      {/* O(1) */}
      <path d="M 20 180 L 270 170" stroke={colors.one} strokeWidth="1.5" fill="none" />
      <text x="275" y="175" fill={colors.one} fontSize="10">O(1)</text>
    </svg>
  );
};

export default ComplexityGraph;