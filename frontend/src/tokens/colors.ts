export const COLOR_TOKENS = {
  bgBase: '#F7F8FA',
  surfaceCard: '#FFFFFF',
  textPrimary: '#12213A',
  textMuted: '#64748B',
  borderDefault: '#E2E8F0',
  borderDark: '#CBD5E1',

  riskTiers: {
    minimal: {
      color: '#065F46',
      bg: '#D1FAE5',
      border: '#6EE7B7',
      gaugeStroke: '#059669',
      label: 'Minimal Risk'
    },
    moderate: {
      color: '#1E40AF',
      bg: '#DBEAFE',
      border: '#93C5FD',
      gaugeStroke: '#2563EB',
      label: 'Moderate Risk'
    },
    elevated: {
      color: '#92400E',
      bg: '#FEF3C7',
      border: '#FCD34D',
      gaugeStroke: '#D97706',
      label: 'Elevated Risk'
    },
    high: {
      color: '#991B1B',
      bg: '#FEE2E2',
      border: '#FCA5A5',
      gaugeStroke: '#B91C1C',
      label: 'High Risk'
    }
  },

  charts: {
    primary: '#12213A',
    secondary: '#475569',
    accent: '#2563EB',
    grid: '#E2E8F0',
    positiveDriver: '#B91C1C', // Increases Risk
    negativeDriver: '#475569', // Decreases Risk
  }
} as const;

export type RiskTierKey = 'Minimal Risk' | 'Moderate Risk' | 'Elevated Risk' | 'High Risk' | 'Low Risk';

export function getRiskTierTheme(tier: string) {
  if (tier === 'High Risk') return COLOR_TOKENS.riskTiers.high;
  if (tier === 'Elevated Risk') return COLOR_TOKENS.riskTiers.elevated;
  if (tier === 'Moderate Risk') return COLOR_TOKENS.riskTiers.moderate;
  return COLOR_TOKENS.riskTiers.minimal;
}
