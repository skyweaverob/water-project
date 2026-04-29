import Link from "next/link";

import { Nav } from "@/components/nav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata = { title: "RFP — Aquaprice" };

export default function RfpDetailPage({ params }: { params: { id: string } }) {
  // Demo. In production this fetches /rfps/{id} and renders the draft content.
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content px-3 py-6">
          <header className="mb-5">
            <p className="text-caption uppercase tracking-wide text-ink-muted">RFP</p>
            <h1 className="mt-half text-title-1 text-ink">
              Aluminum Sulfate Supply Contract — Springfield Water District
            </h1>
            <p className="mt-1 text-body-lg text-ink-muted">
              Draft · Bids due in 14 days · 6 NSF/ANSI 60 suppliers shortlisted
            </p>
          </header>

          <Card>
            <section className="space-y-3">
              <div>
                <p className="text-caption uppercase tracking-wide text-ink-muted">
                  Technical specifications
                </p>
                <ul className="mt-1 list-disc space-y-half pl-3 text-body text-ink">
                  <li>Product shall conform to AWWA B403 — Liquid, Ground, or Lump Aluminum Sulfate.</li>
                  <li>Supplier shall be certified to NSF/ANSI Standard 60 for drinking water treatment.</li>
                  <li>Product shall be supplied as liquid (49% solution).</li>
                  <li>Each delivery shall be accompanied by a Certificate of Analysis.</li>
                </ul>
              </div>
              <div>
                <p className="text-caption uppercase tracking-wide text-ink-muted">
                  Resilience clauses (Low risk band)
                </p>
                <ul className="mt-1 list-disc space-y-half pl-3 text-body text-ink">
                  <li>Supplier shall provide a 30-day notice of any planned production downtime.</li>
                </ul>
              </div>
              <div>
                <p className="text-caption uppercase tracking-wide text-ink-muted">
                  Evaluation weights
                </p>
                <p className="mt-1 text-body text-ink">
                  Price 60% · Technical 20% · Resilience 10% · References 10%
                </p>
              </div>
            </section>
            <div className="mt-4 flex items-center gap-2">
              <Button asChild variant="primary">
                <Link href={`/rfps`}>Download DOCX</Link>
              </Button>
              <Button asChild variant="tertiary">
                <Link href="/rfps">Back to RFPs</Link>
              </Button>
            </div>
          </Card>

          <p className="mt-4 text-caption text-ink-muted">RFP id: {params.id}</p>
        </div>
      </main>
    </>
  );
}
