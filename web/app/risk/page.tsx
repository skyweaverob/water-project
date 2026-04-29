import { Nav } from "@/components/nav";
import { RiskChart } from "@/components/risk-chart";
import { Card } from "@/components/ui/card";
import { RiskDot, type RiskBand } from "@/components/ui/risk-dot";
import { Tbody, Td, Th, Thead, Tr, Table } from "@/components/ui/table";
import { TIMESERIES } from "./demo-data";

export const metadata = { title: "Risk — Aquaprice" };

const PORTFOLIO: { chemical: string; geography: string; band: RiskBand; primary_supplier: string }[] = [
  { chemical: "Chlorine", geography: "U.S. Gulf Coast", band: "Moderate-High", primary_supplier: "Olin Corporation" },
  { chemical: "Sodium Hypochlorite", geography: "Domestic / regional", band: "Moderate-High", primary_supplier: "Odyssey Manufacturing" },
  { chemical: "Phosphoric Acid", geography: "Florida / Idaho", band: "Moderate-High", primary_supplier: "Mosaic" },
  { chemical: "Aluminum Sulfate", geography: "Domestic distributed", band: "Low", primary_supplier: "Chemtrade Solutions" },
  { chemical: "Ferric Chloride", geography: "Domestic distributed", band: "Moderate-Low", primary_supplier: "Kemira" },
  { chemical: "Calcium Hydroxide", geography: "U.S. Midwest", band: "Low", primary_supplier: "Mississippi Lime" },
  { chemical: "Hydrofluorosilicic Acid", geography: "Florida / Louisiana", band: "Moderate-Low", primary_supplier: "Mosaic" },
];

export default function RiskPage() {
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content px-3 py-6">
          <header className="mb-5">
            <h1 className="text-title-1 text-ink">Portfolio risk</h1>
            <p className="mt-1 text-body-lg text-ink-muted">
              90-day composite. Ingests EPA priors, daily web disruption signals, FRED PPI series,
              NOAA tropical cyclone tracks, USGS quakes, and SEC EDGAR force-majeure 8-Ks.
            </p>
          </header>

          <Card>
            <RiskChart data={TIMESERIES} />
          </Card>

          <section className="mt-6">
            <h2 className="text-title-2 text-ink">Portfolio</h2>
            <p className="mt-1 text-body text-ink-muted">
              Sorted by current risk band. Click a chemical to drill into its disruption history.
            </p>
            <Card className="mt-3">
              <Table>
                <Thead>
                  <Tr>
                    <Th>Chemical</Th>
                    <Th>Manufacturing geography</Th>
                    <Th>Primary supplier</Th>
                    <Th className="text-right">Risk</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {PORTFOLIO.map((row) => (
                    <Tr key={row.chemical}>
                      <Td>
                        <p className="text-body-lg font-medium text-ink">{row.chemical}</p>
                      </Td>
                      <Td className="text-ink-muted">{row.geography}</Td>
                      <Td className="text-ink-muted">{row.primary_supplier}</Td>
                      <Td className="text-right">
                        <RiskDot band={row.band} />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Card>
          </section>
        </div>
      </main>
    </>
  );
}
