import { Nav } from "@/components/nav";
import { Card } from "@/components/ui/card";
import { RiskDot } from "@/components/ui/risk-dot";
import { Tbody, Td, Th, Thead, Tr, Table } from "@/components/ui/table";
import { formatCurrency } from "@/lib/utils";

export const metadata = { title: "Bids — Aquaprice" };

// Demo evaluation. Wired to /bids/by-rfp/{id}/evaluate + /market-benchmark in production.
const RFP_TITLE = "Aluminum Sulfate Supply Contract — Springfield Water District";
const MARKET_MEDIAN = 0.41;
const MARKET_SAMPLE_SIZE = 7;
const RISK = "Low" as const;

const BIDS = [
  {
    id: "1",
    supplier: "Chemtrade Solutions",
    origin: "Domestic",
    concentration: "50%",
    rawPrice: "$0.20/lb",
    normalizedActive: 0.412,
    score: 92.4,
    risk: "Low" as const,
    recommended: true,
  },
  {
    id: "2",
    supplier: "USALCO",
    origin: "Domestic",
    concentration: "49%",
    rawPrice: "$0.21/lb",
    normalizedActive: 0.428,
    score: 89.1,
    risk: "Low" as const,
    recommended: false,
  },
  {
    id: "3",
    supplier: "Southern Ionics",
    origin: "Domestic",
    concentration: "48%",
    rawPrice: "$0.22/lb",
    normalizedActive: 0.467,
    score: 84.8,
    risk: "Moderate-Low" as const,
    recommended: false,
  },
  {
    id: "4",
    supplier: "GEO Specialty Chemicals",
    origin: "Domestic",
    concentration: "50%",
    rawPrice: "$0.24/lb",
    normalizedActive: 0.495,
    score: 81.2,
    risk: "Low" as const,
    recommended: false,
  },
];

export default function BidsPage() {
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content-wide px-3 py-6">
          <header className="flex items-end justify-between">
            <div>
              <h1 className="text-title-1 text-ink">Bid Evaluator</h1>
              <p className="mt-1 text-body-lg text-ink-muted">{RFP_TITLE}</p>
            </div>
            <div className="text-right">
              <p className="text-caption uppercase tracking-wide text-ink-muted">
                Live market benchmark
              </p>
              <p className="num text-title-2 text-ink">${MARKET_MEDIAN.toFixed(3)}/kg active</p>
              <p className="text-caption text-ink-muted">
                Median across {MARKET_SAMPLE_SIZE} verified sources · refreshed weekly
              </p>
            </div>
          </header>

          <div className="mt-5">
            <Card>
              <Table>
                <Thead>
                  <Tr>
                    <Th>Supplier</Th>
                    <Th>Origin</Th>
                    <Th>Strength</Th>
                    <Th className="text-right">Quoted</Th>
                    <Th className="text-right">$ / kg active</Th>
                    <Th className="text-right">vs market</Th>
                    <Th className="text-right">Risk</Th>
                    <Th className="text-right">Score</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {BIDS.map((b) => {
                    const delta = ((b.normalizedActive - MARKET_MEDIAN) / MARKET_MEDIAN) * 100;
                    const deltaSign = delta >= 0 ? "+" : "";
                    return (
                      <Tr key={b.id} className={b.recommended ? "border-l-[2px] border-l-accent" : ""}>
                        <Td className={b.recommended ? "pl-2" : ""}>
                          <p className="text-body-lg font-medium text-ink">{b.supplier}</p>
                          <p className="text-caption text-ink-muted">
                            {formatCurrency(b.normalizedActive, { maximumFractionDigits: 3 })} normalized · {b.concentration} solution
                          </p>
                        </Td>
                        <Td className="text-ink-muted">{b.origin}</Td>
                        <Td className="text-ink-muted">{b.concentration}</Td>
                        <Td className="text-right text-ink num">{b.rawPrice}</Td>
                        <Td className="text-right text-ink num">${b.normalizedActive.toFixed(3)}</Td>
                        <Td className="text-right text-ink-muted num">
                          {deltaSign}
                          {delta.toFixed(1)}%
                        </Td>
                        <Td className="text-right">
                          <RiskDot band={b.risk} />
                        </Td>
                        <Td className="text-right text-ink num">{b.score.toFixed(1)}</Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            </Card>
            <p className="mt-2 text-caption text-ink-muted">
              The recommended bid carries a 2px blue left border. The "vs market" column is the
              difference between the supplier's normalized $/kg active and the live web-search-derived
              median. Refreshed weekly by the platform's price-discovery agent.
            </p>
          </div>
        </div>
      </main>
    </>
  );
}
