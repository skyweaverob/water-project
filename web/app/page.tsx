import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="bg-white">
      {/* Hero — black text on white, single sentence, single button */}
      <section className="mx-auto max-w-content px-3 pb-7 pt-8">
        <h1 className="max-w-prose text-display-xl font-semibold tracking-tight text-ink">
          Procurement intelligence for water treatment chemicals.
        </h1>
        <p className="mt-3 max-w-prose text-title-2 font-regular text-ink-muted">
          Write defensible RFPs. Evaluate bids on real cost per kilogram of active
          ingredient. Watch your supply chain before it breaks.
        </p>
        <div className="mt-5">
          <Button asChild variant="primary">
            <Link href="/dashboard">See the platform</Link>
          </Button>
        </div>
      </section>

      {/* Photographic hero — placeholder cool/desaturated treatment-plant gradient. Replace
          with a licensed photograph in production. */}
      <section
        className="h-[480px] w-full"
        style={{
          background:
            "linear-gradient(180deg, rgba(29,29,31,0.05) 0%, rgba(29,29,31,0.18) 100%), linear-gradient(135deg, #B6C2CE 0%, #6E7B89 60%, #3A4651 100%)",
        }}
        aria-label="Water treatment plant"
      />

      {/* Three feature sections */}
      <Feature
        title="Write better RFPs in minutes."
        body="Describe your facility — sector, flow, treatment processes, current chemicals.
        The platform drafts a procurement-ready RFP package: technical specs, supply-resilience
        clauses scaled to chemical risk, evaluation criteria, and contract boilerplate. Edit
        and download as DOCX."
      />
      <Feature
        title="Evaluate bids on real cost."
        body="Drop in supplier responses. The platform extracts pricing, normalizes to dollars
        per kilogram of delivered active ingredient, flags non-conforming bids, and produces a
        risk-adjusted award memo your board or procurement office can sign."
      />
      <Feature
        title="See risk early."
        body="Daily background analysis pulls public news, NOAA weather, EIA refinery data, and
        BLS feedstock indices, and cross-references your portfolio. You learn about a
        feedstock disruption before it shows up at your delivery dock."
      />

      {/* Pricing */}
      <section className="border-t border-border-subtle py-8">
        <div className="mx-auto max-w-content px-3">
          <h2 className="text-title-1 text-ink">Pricing</h2>
          <p className="mt-1 text-body-lg text-ink-muted">
            Annual subscription. No setup fees. No usage caps inside your tier.
          </p>
          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
            <PriceCard
              tier="Single facility"
              price="$8,000"
              note="Per facility per year. 5 seats."
              points={[
                "RFP Builder, Bid Evaluator, Knowledge Q&A",
                "Risk Monitor with daily portfolio scoring",
                "Email and Slack alert delivery",
              ]}
            />
            <PriceCard
              tier="Multi-facility"
              price="$40,000"
              note="Up to 25 facilities. Unlimited seats."
              points={[
                "Everything in Single Facility",
                "Multi-facility rollup dashboards",
                "Quarterly board-ready PDF reports",
                "API access for ERP and ESG reporting",
              ]}
              recommended
            />
            <PriceCard
              tier="Enterprise"
              price="Custom"
              note="Talk to us."
              points={[
                "Single sign-on, audit logging",
                "Dedicated solutions engineer",
                "Custom verticals and report templates",
                "On-prem deployment available",
              ]}
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-subtle">
        <div className="mx-auto flex max-w-content items-center justify-between px-3 py-3">
          <p className="text-caption text-ink-muted">© 2026 Aquaprice</p>
          <nav className="flex items-center gap-3 text-caption text-ink-muted">
            <Link href="/design" className="hover:text-ink">Design system</Link>
            <Link href="/dashboard" className="hover:text-ink">Sign in</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <section className="py-7 md:py-8">
      <div className="mx-auto max-w-prose px-3 text-center">
        <h2 className="text-title-1 text-ink">{title}</h2>
        <p className="mt-2 text-body-lg text-ink-muted">{body}</p>
      </div>
    </section>
  );
}

function PriceCard({
  tier,
  price,
  note,
  points,
  recommended = false,
}: {
  tier: string;
  price: string;
  note: string;
  points: string[];
  recommended?: boolean;
}) {
  return (
    <div
      className={`rounded-md bg-white p-4 shadow-card ${
        recommended ? "border-2 border-accent" : ""
      }`}
    >
      <p className="text-body text-ink-muted">{tier}</p>
      <p className="mt-1 text-display font-semibold text-ink">{price}</p>
      <p className="mt-half text-caption text-ink-muted">{note}</p>
      <ul className="mt-3 space-y-1 text-body text-ink">
        {points.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  );
}
