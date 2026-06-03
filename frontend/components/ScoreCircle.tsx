
import React from 'react';
import GradientText from './GradientText';
import { useTheme } from '../contexts/ThemeContext';

interface ScoreCircleProps {
  score: number;
  maxScore?: number;
}

const gradientColors = {
  dark: {
    stop1: '#7AA2F7',
    stop2: '#BB9AF7',
  },
  light: {
    stop1: '#3B82F6',
    stop2: '#A78BFA',
  }
}

const ScoreCircle: React.FC<ScoreCircleProps> = ({ score, maxScore = 100 }) => {
  const { theme } = useTheme();
  const colors = theme === 'light' ? gradientColors.light : gradientColors.dark;

  const radius = 80;
  const strokeWidth = 12;
  const innerRadius = radius - strokeWidth / 2;
  const circumference = 2 * Math.PI * innerRadius;
  const offset = circumference - (score / maxScore) * circumference;

  return (
    <div className="relative flex items-center justify-center w-52 h-52">
      <svg className="absolute w-full h-full transform -rotate-90" viewBox={`0 0 ${radius*2} ${radius*2}`}>
        <defs>
            <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={colors.stop1} />
                <stop offset="100%" stopColor={colors.stop2} />
            </linearGradient>
        </defs>
        <circle
          className="text-text-secondary/20 dark:text-text-secondary/50"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          r={innerRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke="url(#scoreGradient)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="transparent"
          r={innerRadius}
          cx={radius}
          cy={radius}
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: offset,
            transition: 'stroke-dashoffset 0.8s ease-out',
          }}
        />
      </svg>
      <div className="text-center">
         <p className="text-sm text-text-secondary">Global Quality Score</p>
         <GradientText as="h2" className="text-5xl font-bold">{score}/{maxScore}</GradientText>
      </div>
    </div>
  );
};

export default ScoreCircle;