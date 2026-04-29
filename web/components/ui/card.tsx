import * as React from "react";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }
>(({ className, interactive = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-md bg-white shadow-card p-4 md:p-4",
      interactive && "transition-shadow duration-quick ease-out hover:shadow-card-hover",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("space-y-2", className)} {...props} />,
);
CardBody.displayName = "CardBody";
