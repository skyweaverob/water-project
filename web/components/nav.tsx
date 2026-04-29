"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/rfps", label: "RFPs" },
  { href: "/bids", label: "Bids" },
  { href: "/risk", label: "Risk" },
  { href: "/knowledge", label: "Knowledge" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="nav-surface fixed inset-x-0 top-0 z-[100] h-nav">
      <div className="mx-auto flex h-full max-w-content-wide items-center justify-between px-3">
        <Link href="/" className="text-body font-semibold tracking-snug text-ink">
          Aquaprice
        </Link>
        <nav className="flex items-center gap-3">
          {NAV_ITEMS.map((item) => {
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "text-body transition-colors duration-quick ease-out",
                  active ? "text-ink font-medium" : "text-ink-muted hover:text-ink",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/account" className="text-body text-ink-muted hover:text-ink transition-colors duration-quick">
            Account
          </Link>
        </div>
      </div>
    </header>
  );
}
