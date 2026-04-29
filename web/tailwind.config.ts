import type { Config } from "tailwindcss";
import animatePlugin from "tailwindcss-animate";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./styles/**/*.{ts,tsx}",
  ],
  theme: {
    // Replace, don't extend — restrict the palette to design-token values only.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#FFFFFF",
      black: "#000000",
      bg: {
        DEFAULT: "#FFFFFF",
        muted: "#FAFAFA",
        subtle: "#F5F5F7",
      },
      ink: {
        DEFAULT: "#1D1D1F",
        muted: "#86868B",
        subtle: "#AEAEB2",
      },
      accent: {
        DEFAULT: "#0071E3",
        hover: "#0058B0",
        muted: "rgba(0, 113, 227, 0.08)",
        focus: "rgba(0, 113, 227, 0.20)",
      },
      border: {
        DEFAULT: "#D2D2D7",
        subtle: "#F5F5F7",
      },
      status: {
        low: "#34C759",
        moderate: "#FFCC00",
        elevated: "#FF9500",
      },
    },
    fontFamily: {
      sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
    },
    fontSize: {
      caption: ["13px", { lineHeight: "18px", letterSpacing: "0" }],
      body: ["15px", { lineHeight: "22px", letterSpacing: "0" }],
      "body-lg": ["17px", { lineHeight: "26px", letterSpacing: "0" }],
      "title-3": ["20px", { lineHeight: "28px", fontWeight: "600", letterSpacing: "0" }],
      "title-2": ["24px", { lineHeight: "32px", fontWeight: "600", letterSpacing: "-0.01em" }],
      "title-1": ["32px", { lineHeight: "40px", fontWeight: "600", letterSpacing: "-0.015em" }],
      display: ["48px", { lineHeight: "56px", fontWeight: "600", letterSpacing: "-0.02em" }],
      "display-xl": ["56px", { lineHeight: "64px", fontWeight: "600", letterSpacing: "-0.02em" }],
      numerical: ["40px", { lineHeight: "48px", fontWeight: "600", letterSpacing: "-0.015em" }],
    },
    fontWeight: {
      regular: "400",
      medium: "500",
      semibold: "600",
    },
    letterSpacing: {
      tight: "-0.02em",
      snug: "-0.015em",
      normal: "-0.01em",
      relaxed: "0",
      wide: "0.05em",
    },
    spacing: {
      "0": "0",
      "1": "8px",
      "2": "16px",
      "3": "24px",
      "4": "32px",
      "5": "48px",
      "6": "64px",
      "7": "96px",
      "8": "128px",
      px: "1px",
      half: "4px",
      nav: "56px",
    },
    borderRadius: {
      none: "0",
      sm: "6px",
      md: "8px",
      lg: "16px",
      pill: "980px",
      full: "9999px",
    },
    boxShadow: {
      none: "none",
      card: "0 1px 3px rgba(0, 0, 0, 0.04)",
      "card-hover": "0 4px 16px rgba(0, 0, 0, 0.08)",
      modal: "0 20px 60px rgba(0, 0, 0, 0.16)",
      focus: "0 0 0 4px rgba(0, 113, 227, 0.20)",
    },
    extend: {
      maxWidth: {
        content: "1080px",
        "content-wide": "1280px",
        form: "720px",
        prose: "640px",
      },
      backdropBlur: {
        nav: "20px",
        modal: "8px",
      },
      transitionDuration: {
        quick: "200ms",
        standard: "300ms",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [animatePlugin],
};

export default config;
