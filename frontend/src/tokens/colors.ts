export const COLOR_TOKENS = {
  bgBase: '#F7F8FA',
  surfaceCard: '#FFFFFF',
  textPrimary: '#12213A',
  textMuted: '#64748B',
  borderDefault: '#E2E8F0',
  borderDark: '#CBD5E1',

  riskTiers: {
    low: {
      color: '#475569',
      bg: '#F1F5F9',
      border: '#CBD5E1',
      gaugeStroke: '#64748B',
      label: 'Low Risk'
    },
    moderate: {
      color: '#B45309',
      bg: '#FEF3C7',
      border: '#FDE68A',
      gaugeStroke: '#D97706',
      label: 'Moderate Risk'
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

export type RiskTierKey = 'Low Risk' | 'Moderate Risk' | 'High Risk';

export function getRiskTierTheme(tier: string) {
  if (tier === 'High Risk') return COLOR_TOKENS.riskTiers.high;
  if (tier === 'Moderate Risk') return COLOR_TOKENS.riskTiers.moderate;
  return COLOR_TOKENS.riskTiers.low;
}
