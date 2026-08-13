import React from 'react';
import { getRiskTierTheme } from '../tokens/colors';

interface ScoreGaugeProps {
  probability: number;
  tier: 'Low Risk' | 'Moderate Risk' | 'High Risk';
  threshold?: number;
  variant?: 'compact' | 'full';
  showLabel?: boolean;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  probability,
  tier,
  threshold = 0.2021,
  variant = 'compact',
  showLabel = true,
}) => {
  const theme = getRiskTierTheme(tier);
  const scorePct = Math.round(probability * 100);

  if (variant === 'compact') {
    const radius = 18;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (probability * circumference);

    return (
      <div className="flex items-center gap-2">
        <div className="relative w-10 h-10 flex items-center justify-center">
          <svg className="w-10 h-10 transform -rotate-90" viewBox="0 0 44 44">
            <circle
              cx="22"
              cy="22"
              r={radius}
              className="stroke-slate-200"
              strokeWidth="4.5"
              fill="transparent"
            />
            <circle
              cx="22"
              cy="22"
              r={radius}
              stroke={theme.gaugeStroke}
              strokeWidth="4.5"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
              className="transition-all duration-700 ease-out"
            />
          </svg>
          <span className="absolute font-mono text-[11px] font-bold text-[#12213A] tabular-nums">
            {scorePct}%
          </span>
        </div>
        {showLabel && (
          <span
            className="px-2 py-0.5 text-xs font-semibold rounded border tabular-nums"
            style={{
              backgroundColor: theme.bg,
              color: theme.color,
              borderColor: theme.border,
            }}
          >
            {tier}
          </span>
        )}
      </div>
    );
  }

  // Full SVG Arc Gauge (180 Degree Semi-Circle)
  const arcRadius = 65;
  const arcLength = Math.PI * arcRadius;
  const activeOffset = arcLength - (probability * arcLength);
  const threshAngle = Math.PI * (1 - threshold);
  const threshX = 90 + arcRadius * Math.cos(threshAngle);
  const threshY = 85 - arcRadius * Math.sin(threshAngle);

  return (
    <div className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
      <div className="relative w-[180px] h-[105px] flex items-center justify-center">
        <svg className="w-[180px] h-[110px]" viewBox="0 0 180 110">
          {/* Background Arc */}
          <path
            d="M 25 85 A 65 65 0 0 1 155 85"
            fill="none"
            stroke="#E2E8F0"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Active Probability Arc */}
          <path
            d="M 25 85 A 65 65 0 0 1 155 85"
            fill="none"
            stroke={theme.gaugeStroke}
            strokeWidth="12"
            strokeDasharray={arcLength}
            strokeDashoffset={activeOffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
          {/* Threshold Marker Indicator */}
          <line
            x1={threshX}
            y1={threshY - 6}
            x2={threshX}
            y2={threshY + 6}
            stroke="#12213A"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
        {/* Score Display Center */}
        <div className="absolute top-[48px] flex flex-col items-center">
          <span className="font-mono text-3xl font-bold tracking-tight text-[#12213A] tabular-nums">
            {scorePct}%
          </span>
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
            Readmission Risk
          </span>
        </div>
      </div>

      {/* Risk Badge and Threshold Legend */}
      <div className="mt-2 flex items-center gap-3">
        <span
          className="px-3 py-1 text-xs font-semibold rounded-md border shadow-xs"
          style={{
            backgroundColor: theme.bg,
            color: theme.color,
            borderColor: theme.border,
          }}
        >
          {tier}
        </span>
        <span className="text-xs text-slate-500 font-mono">
          Cutoff: <span className="font-bold text-slate-700">{(threshold * 100).toFixed(1)}%</span>
        </span>
      </div>
    </div>
  );
};
