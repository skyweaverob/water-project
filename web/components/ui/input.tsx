import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "h-[44px] w-full rounded-sm border border-border bg-white px-2 text-body text-ink placeholder:text-ink-muted",
        "transition-colors duration-quick ease-out",
        "focus:border-accent focus:shadow-focus focus:outline-none",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-[88px] w-full rounded-sm border border-border bg-white px-2 py-1 text-body text-ink placeholder:text-ink-muted",
        "transition-colors duration-quick ease-out",
        "focus:border-accent focus:shadow-focus focus:outline-none",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

export const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("block text-caption uppercase tracking-wide text-ink-muted mb-half", className)}
      {...props}
    />
  ),
);
Label.displayName = "Label";

export function HelperText({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "warn" }) {
  return (
    <p className={cn("mt-half text-caption", tone === "warn" ? "text-status-elevated" : "text-ink-muted")}>{children}</p>
  );
}
