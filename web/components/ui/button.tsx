import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap font-medium transition-colors duration-quick ease-out disabled:pointer-events-none disabled:opacity-40",
  {
    variants: {
      variant: {
        // Primary: pill, system blue, white text. Never more than one per screen.
        primary:
          "rounded-pill bg-accent text-white text-body-lg hover:bg-accent-hover px-3 py-1 min-h-[44px] tracking-normal",
        // Secondary: pill, transparent, blue text, faint hover.
        secondary:
          "rounded-pill bg-transparent text-accent text-body-lg hover:bg-bg-subtle px-3 py-1 min-h-[44px]",
        // Tertiary: text link in blue, underline on hover.
        tertiary:
          "bg-transparent text-accent text-body-lg hover:underline underline-offset-4 px-0 py-0 h-auto",
        // Ghost: low-key icon button or inline action
        ghost:
          "rounded-md bg-transparent text-ink hover:bg-bg-subtle px-2 py-1 text-body min-h-[36px]",
      },
      size: {
        default: "",
        sm: "min-h-[36px] text-body px-2 py-half",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";
