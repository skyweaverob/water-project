import Link from "next/link";

import { Nav } from "@/components/nav";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";

// Demo data — wired through the API in production.
const NEXT_ACTION = {
  headline: "Aluminum sulfate bid window closes in 6 days.",
  cta: "Open Bid Evaluator",
  href: "/bids",
};

const STATS = [
  { value: 12, label: "Active contracts" },
  { value: 28, label: "Chemicals tracked" },
  { value: 47, label: "Portfolio risk score" },
];

// Pre-formatted relative timestamps avoid server/client hydration mismatches that would
// happen if we computed Date.now() during render.
const ACTIVITY: { title: string; at: string }[] = [
  { title: "Chemtrade submitted bid for Aluminum Sulfate RFP", at: "90 minutes ago" },
  { title: "RFP — Sodium Hypochlorite — Springfield Water moved to evaluation", at: "6 hours ago" },
  { title: "Risk score rose from 41 to 47 (chlorine portfolio)", at: "14 hours ago" },
  { title: "Award memo generated for Ferric Chloride contract", at: "1 day ago" },
  { title: "Knowledge query — bauxite import partners", at: "1 day ago" },
];

export const metadata = { title: "Dashboard — Aquaprice" };

export default function DashboardPage() {
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content px-3 py-6">
          <Card>
            <p className="text-title-2 font-regular text-ink">{NEXT_ACTION.headline}</p>
            <div className="mt-3">
              <Button asChild variant="primary">
                <Link href={NEXT_ACTION.href}>{NEXT_ACTION.cta}</Link>
              </Button>
            </div>
          </Card>

          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
            {STATS.map((s) => (
              <Card key={s.label}>
                <CardBody>
                  <p className="text-numerical text-ink num">{s.value}</p>
                  <p className="text-caption uppercase tracking-wide text-ink-muted">{s.label}</p>
                </CardBody>
              </Card>
            ))}
          </div>

          <section className="mt-6">
            <h2 className="text-title-2 text-ink">Recent activity</h2>
            <ul className="mt-2 divide-y divide-border-subtle">
              {ACTIVITY.map((a) => (
                <li key={a.title} className="flex items-baseline justify-between gap-3 py-2">
                  <p className="text-body text-ink">{a.title}</p>
                  <p className="text-caption text-ink-muted whitespace-nowrap">{a.at}</p>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </main>
    </>
  );
}
