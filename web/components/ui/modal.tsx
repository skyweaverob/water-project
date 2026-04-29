"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

export const Modal = Dialog.Root;
export const ModalTrigger = Dialog.Trigger;

export const ModalContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentPropsWithoutRef<typeof Dialog.Content>
>(({ className, children, ...props }, ref) => (
  <Dialog.Portal>
    <Dialog.Overlay
      className={cn(
        "fixed inset-0 z-[1000] bg-black/40 backdrop-blur-modal",
        "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
      )}
    />
    <Dialog.Content
      ref={ref}
      className={cn(
        "fixed left-1/2 top-1/2 z-[1001] -translate-x-1/2 -translate-y-1/2",
        "w-full max-w-[560px] rounded-lg bg-white p-5 shadow-modal",
        "focus:outline-none",
        "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
        className,
      )}
      {...props}
    >
      {children}
    </Dialog.Content>
  </Dialog.Portal>
));
ModalContent.displayName = "ModalContent";

export const ModalTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <Dialog.Title className={cn("text-title-2 text-ink mb-2", className)} {...props} />
);

export const ModalDescription = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
  <Dialog.Description className={cn("text-body-lg text-ink-muted", className)} {...props} />
);
