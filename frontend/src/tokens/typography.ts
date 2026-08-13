export const TYPOGRAPHY_TOKENS = {
  fontDisplay: "'IBM Plex Sans', 'Inter', sans-serif",
  fontBody: "'Inter', system-ui, sans-serif",
  fontMono: "'JetBrains Mono', 'IBM Plex Mono', monospace",

  headings: {
    pageTitle: "text-2xl font-bold tracking-tight text-[#12213A] font-display",
    sectionTitle: "text-lg font-semibold text-[#12213A] font-display",
    cardTitle: "text-base font-semibold text-[#12213A] font-display",
    subheading: "text-sm font-medium text-[#64748B]",
  },
  body: {
    base: "text-sm text-[#12213A] leading-relaxed",
    muted: "text-xs text-[#64748B]",
    bold: "text-sm font-semibold text-[#12213A]",
  },
  tabular: {
    score: "font-mono font-bold tracking-tight tabular-nums",
    value: "font-mono text-sm text-[#12213A] tabular-nums",
  }
} as const;
