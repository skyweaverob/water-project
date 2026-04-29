import { cn } from "@/lib/utils";

export type RiskBand = "Low" | "Moderate-Low" | "Moderate" | "Moderate-High" | "High";

const BAND_TO_CLASS: Record<RiskBand, string> = {
  Low: "bg-status-low",
  "Moderate-Low": "bg-status-low",
  Moderate: "bg-status-moderate",
  "Moderate-High": "bg-status-elevated",
  High: "bg-status-elevated",
};

export function RiskDot({ band, className }: { band: RiskBand; className?: string }) {
  // 8px dot. Tailwind's h-1/w-1 in our scale = 8px (the design token).
  return (
    <span
      className={cn("inline-block h-1 w-1 rounded-full align-middle", BAND_TO_CLASS[band], className)}
      aria-label={`Risk: ${band}`}
      role="img"
    />
  );
}
