import Link from "next/link";

import { Nav } from "@/components/nav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Tbody, Td, Th, Thead, Tr, Table } from "@/components/ui/table";

export const metadata = { title: "RFPs — Aquaprice" };

// Demo seeded list. Wired to /rfps API in production.
const RFPS = [
  { id: "1", chemical: "Aluminum Sulfate", facility: "Springfield Water", quantity: 2_500_000, due: "2026-05-12", status: "draft" },
  { id: "2", chemical: "Sodium Hypochlorite", facility: "Eastside Treatment", quantity: 720_000, due: "2026-05-19", status: "published" },
  { id: "3", chemical: "Ferric Chloride", facility: "Northbank Wastewater", quantity: 1_100_000, due: "2026-04-30", status: "evaluation" },
];

export default function RfpsPage() {
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content px-3 py-6">
          <header className="flex items-end justify-between">
            <div>
              <h1 className="text-title-1 text-ink">RFPs</h1>
              <p className="mt-1 text-body-lg text-ink-muted">
                Drafts, published solicitations, and contracts in evaluation.
              </p>
            </div>
            <Button asChild variant="primary">
              <Link href="/rfps/new">New RFP</Link>
            </Button>
          </header>

          <div className="mt-5">
            {RFPS.length === 0 ? (
              <Card>
                <EmptyState
                  message="No RFPs yet."
                  action={
                    <Button asChild variant="tertiary">
                      <Link href="/rfps/new">Start your first RFP</Link>
                    </Button>
                  }
                />
              </Card>
            ) : (
              <Card>
                <Table>
                  <Thead>
                    <Tr>
                      <Th>Chemical</Th>
                      <Th>Facility</Th>
                      <Th className="text-right">Annual kg</Th>
                      <Th>Bids due</Th>
                      <Th>Status</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {RFPS.map((r) => (
                      <Tr key={r.id}>
                        <Td>
                          <Link href={`/rfps/${r.id}`} className="text-body-lg font-medium text-ink hover:text-accent">
                            {r.chemical}
                          </Link>
                        </Td>
                        <Td className="text-ink-muted">{r.facility}</Td>
                        <Td className="text-right num">{r.quantity.toLocaleString()}</Td>
                        <Td className="text-ink-muted">{r.due}</Td>
                        <Td>
                          <span className="text-caption uppercase tracking-wide text-ink-muted">{r.status}</span>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Card>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
