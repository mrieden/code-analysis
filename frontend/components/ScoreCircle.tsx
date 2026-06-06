import React from 'react';
import GradientText from './GradientText';
import { useTheme } from '../contexts/ThemeContext';

interface ScoreCircleProps {
  score: number;
  maxScore?: number;
  variant?: 'default' | 'green';
  /**
   * When provided, the ring is drawn as two segments: the portion up to
   * `baseScore` uses the default gradient, and the *gained* portion
   * (baseScore → score) is drawn in green to highlight the improvement.
   * A "+delta gained" badge is shown under the score.
   */
  baseScore?: number;
}

const gradientColors = {
  dark:  { stop1: '#7AA2F7', stop2: '#BB9AF7' },
  light: { stop1: '#3B82F6', stop2: '#A78BFA' },
  green: { stop1: '#10b981', stop2: '#34d399' },
};

const ScoreCircle: React.FC<ScoreCircleProps> = ({
  score,
  maxScore = 100,
  variant = 'default',
  baseScore,
}) => {
  const { theme } = useTheme();
  const baseColors = variant === 'green'
    ? gradientColors.green
    : theme === 'light' ? gradientColors.light : gradientColors.dark;

  const radius = 80;
  const strokeWidth = 12;
  const innerRadius = radius - strokeWidth / 2;
  const circumference = 2 * Math.PI * innerRadius;

  const clamp = (v: number) => Math.max(0, Math.min(maxScore, v));
  const scoreVal = clamp(score);

  // Decide whether to render a segmented (base + gained) ring.
  const hasBase  = baseScore !== undefined && baseScore !== null;
  const baseVal  = hasBase ? clamp(baseScore as number) : 0;
  const delta    = hasBase ? Math.round(scoreVal - baseVal) : 0;
  const showGain = hasBase && delta > 0;

  // Arc lengths along the circle.
  const fullLen = (scoreVal / maxScore) * circumference;
  const baseLen = (baseVal / maxScore) * circumference;
  const gainLen = Math.max(0, fullLen - baseLen);

  // Pre-computed inline styles (kept as variables to avoid inline literals).
  const baseSegmentStyle: React.CSSProperties = {
    strokeDasharray: `${baseLen} ${circumference}`,
    strokeDashoffset: 0,
  };
  const gainSegmentStyle: React.CSSProperties = {
    strokeDasharray: `${gainLen} ${circumference}`,
    strokeDashoffset: -baseLen,
  };
  const fullArcStyle: React.CSSProperties = {
    strokeDasharray: circumference,
    strokeDashoffset: circumference - fullLen,
  };

  return (
    <div className="relative flex items-center justify-center w-52 h-52">
      <svg className="absolute w-full h-full transform -rotate-90" viewBox={`0 0 ${radius * 2} ${radius * 2}`}>
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={baseColors.stop1} />
            <stop offset="100%" stopColor={baseColors.stop2} />
          </linearGradient>
          <linearGradient id="scoreGradientGain" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={gradientColors.green.stop1} />
            <stop offset="100%" stopColor={gradientColors.green.stop2} />
          </linearGradient>
        </defs>

        {/* Track */}
        <circle
          className="text-text-secondary/20 dark:text-text-secondary/50"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="transparent"
          r={innerRadius}
          cx={radius}
          cy={radius}
        />

        {showGain ? (
          <>
            {/* Base segment (previous score) */}
            <circle
              stroke="url(#scoreGradient)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              fill="transparent"
              r={innerRadius}
              cx={radius}
              cy={radius}
              style={baseSegmentStyle}
            />
            {/* Gained segment (added score) drawn in green */}
            <circle
              stroke="url(#scoreGradientGain)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              fill="transparent"
              r={innerRadius}
              cx={radius}
              cy={radius}
              style={gainSegmentStyle}
            />
          </>
        ) : (
          <circle
            stroke="url(#scoreGradient)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            fill="transparent"
            r={innerRadius}
            cx={radius}
            cy={radius}
            style={fullArcStyle}
          />
        )}
      </svg>

      <div className="text-center">
        <p className="text-sm text-text-secondary">Global Quality Score</p>
        <GradientText as="h2" className="text-5xl font-bold">{Math.round(scoreVal)}/{maxScore}</GradientText>
        {showGain && (
          <p className="text-sm font-bold text-green-400 mt-1">+{delta} gained</p>
        )}
      </div>
    </div>
  );
};

export default ScoreCircle;
