/**
 * Design tokens — Apple iOS 8 / OS X Yosemite era, restrained and confident.
 *
 * These are the *only* values allowed in the UI. No arbitrary spacing, no off-palette colors,
 * no font sizes outside the scale. If you find yourself wanting something not in this file,
 * the answer is almost always that the layout needs more whitespace or a different hierarchy,
 * not a new token.
 */

export const color = {
  // Backgrounds
  bgPrimary: "#FFFFFF",
  bgSecondary: "#FAFAFA",
  bgTertiary: "#F5F5F7",

  // Text — true black for primary, warm gray for secondary, never pure gray
  textPrimary: "#1D1D1F",
  textSecondary: "#86868B",
  textTertiary: "#AEAEB2",

  // Accent — single restrained system blue, used sparingly for primary actions only
  accent: "#0071E3",
  accentHover: "#0058B0",
  accentMuted: "rgba(0, 113, 227, 0.08)",
  accentFocus: "rgba(0, 113, 227, 0.20)",

  // Borders / hairlines
  border: "#D2D2D7",
  divider: "#F5F5F7",

  // Status — calm, never alarming. The only place color carries semantic meaning.
  statusLow: "#34C759",      // calm green
  statusModerate: "#FFCC00", // warm yellow
  statusElevated: "#FF9500", // amber, never red

  // Shadows
  shadowCard: "0 1px 3px rgba(0, 0, 0, 0.04)",
  shadowCardHover: "0 4px 16px rgba(0, 0, 0, 0.08)",
  shadowModal: "0 20px 60px rgba(0, 0, 0, 0.16)",
} as const;

export const spacing = {
  // 8px baseline grid. Never arbitrary.
  s0: "0",
  s1: "8px",
  s2: "16px",
  s3: "24px",
  s4: "32px",
  s5: "48px",
  s6: "64px",
  s7: "96px",
  s8: "128px",
} as const;

export const radius = {
  input: "6px",
  card: "8px",
  modal: "16px",
  pill: "980px",
} as const;

export const shadow = {
  card: color.shadowCard,
  cardHover: color.shadowCardHover,
  modal: color.shadowModal,
} as const;

export const font = {
  family: "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  weight: {
    regular: 400,
    medium: 500,
    semibold: 600,
  },
  // Letter spacing tightens with size, Apple-style
  letter: {
    tight: "-0.02em",
    snug: "-0.015em",
    normal: "-0.01em",
    relaxed: "0",
    wide: "0.05em",
  },
} as const;

/**
 * Typography scale. Use the named role, not the raw size.
 * fontSize tuple is [size, lineHeight]. Lines are absolute, not unitless.
 */
export const type = {
  display: { size: "48px", line: "56px", weight: 600, letter: "-0.02em" },
  title1: { size: "32px", line: "40px", weight: 600, letter: "-0.015em" },
  title2: { size: "24px", line: "32px", weight: 600, letter: "-0.01em" },
  title3: { size: "20px", line: "28px", weight: 600, letter: "0" },
  bodyLarge: { size: "17px", line: "26px", weight: 400, letter: "0" },
  body: { size: "15px", line: "22px", weight: 400, letter: "0" },
  caption: { size: "13px", line: "18px", weight: 400, letter: "0" },
  numericalLg: { size: "40px", line: "48px", weight: 600, letter: "-0.015em" },
} as const;

export const motion = {
  duration: {
    quick: "200ms",
    standard: "300ms",
  },
  easing: {
    out: "cubic-bezier(0.16, 1, 0.3, 1)",
    standard: "cubic-bezier(0.4, 0, 0.2, 1)",
  },
} as const;

export const layout = {
  // Top nav is the only chrome. No sidebars.
  navHeight: "56px",
  contentMax: "1080px",
  contentMaxWide: "1280px",      // Bid Evaluator and other data-dense pages only
  formMax: "720px",              // RFP Builder
  prosePage: "640px",            // Knowledge Q&A response
} as const;

export const z = {
  base: 0,
  raised: 10,
  nav: 100,
  dialog: 1000,
  toast: 2000,
} as const;

/**
 * Risk-rating color mapping.
 *
 * The design rule: status color appears only on the Risk Monitor and Bid Evaluator,
 * never anywhere else. Risk dots use these tokens; nothing else does.
 */
export const riskColor = {
  Low: color.statusLow,
  "Moderate-Low": color.statusLow,
  Moderate: color.statusModerate,
  "Moderate-High": color.statusElevated,
  High: color.statusElevated,
} as const;

export type RiskBand = keyof typeof riskColor;
