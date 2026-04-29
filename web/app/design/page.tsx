import Link from "next/link";
import { ArrowRight, FileText, ShieldCheck, Sparkles } from "lucide-react";

import { Nav } from "@/components/nav";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { HelperText, Input, Label, Textarea } from "@/components/ui/input";
import { Modal, ModalContent, ModalDescription, ModalTitle, ModalTrigger } from "@/components/ui/modal";
import { RiskDot } from "@/components/ui/risk-dot";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";

export const metadata = { title: "Design system — Aquaprice" };

export default function DesignPage() {
  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-content px-3 py-6">
          <header className="mb-6">
            <h1 className="text-title-1 text-ink">Design system</h1>
            <p className="mt-1 text-body-lg text-ink-muted">
              Reference page for every component, type ramp, color, and motion the product uses.
              Every screen is built from these pieces; nothing else.
            </p>
          </header>

          <Section title="Typography" caption="Type does most of the work">
            <div className="space-y-3">
              <Specimen sample="Procurement intelligence" role="Display, 48 / 56 / 600 / -0.02em" className="text-display" />
              <Specimen sample="Risk Monitor" role="Title 1, 32 / 40 / 600 / -0.015em" className="text-title-1" />
              <Specimen sample="Recent activity" role="Title 2, 24 / 32 / 600 / -0.01em" className="text-title-2" />
              <Specimen sample="Supplier" role="Title 3, 20 / 28 / 600" className="text-title-3" />
              <Specimen
                sample="Aluminum sulfate is the most widely used coagulant in U.S. drinking water treatment."
                role="Body large, 17 / 26 / 400"
                className="text-body-lg"
              />
              <Specimen
                sample="Used as a primary coagulant; ~45% of total domestic consumption goes to the water sector."
                role="Body, 15 / 22 / 400"
                className="text-body"
              />
              <Specimen sample="HTS 2833.22 · 25% Section 301" role="Caption, 13 / 18 / 400" className="text-caption text-ink-muted" />
              <div className="flex items-baseline gap-3 pt-2">
                <p className="text-numerical text-ink num">1,247,500</p>
                <p className="text-caption uppercase tracking-wide text-ink-muted">Numerical, 40 / 48 / 600 — tabular</p>
              </div>
            </div>
          </Section>

          <Section title="Color" caption="Mostly absence of color">
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              <Swatch name="bg/DEFAULT" hex="#FFFFFF" />
              <Swatch name="bg/muted" hex="#FAFAFA" />
              <Swatch name="bg/subtle" hex="#F5F5F7" />
              <Swatch name="border" hex="#D2D2D7" />
              <Swatch name="ink" hex="#1D1D1F" />
              <Swatch name="ink/muted" hex="#86868B" />
              <Swatch name="ink/subtle" hex="#AEAEB2" />
              <Swatch name="accent" hex="#0071E3" />
              <Swatch name="accent/hover" hex="#0058B0" />
              <Swatch name="status/low" hex="#34C759" />
              <Swatch name="status/moderate" hex="#FFCC00" />
              <Swatch name="status/elevated" hex="#FF9500" />
            </div>
          </Section>

          <Section title="Spacing" caption="8-pixel baseline grid">
            <div className="space-y-1">
              {[
                ["s1", 8],
                ["s2", 16],
                ["s3", 24],
                ["s4", 32],
                ["s5", 48],
                ["s6", 64],
                ["s7", 96],
                ["s8", 128],
              ].map(([token, px]) => (
                <div key={token as string} className="flex items-center gap-3">
                  <span className="w-12 text-caption text-ink-muted">{token}</span>
                  <span className="block bg-accent" style={{ width: `${px}px`, height: "8px" }} />
                  <span className="text-caption text-ink-muted num">{px}px</span>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Buttons" caption="One primary per screen, never more">
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="primary">Generate RFP</Button>
              <Button variant="secondary">Save draft</Button>
              <Button variant="tertiary">Cancel</Button>
              <Button variant="ghost">
                <Sparkles className="mr-1 h-[16px] w-[16px]" strokeWidth={1.5} />
                Suggest
              </Button>
              <Button variant="primary" disabled>
                Disabled
              </Button>
            </div>
          </Section>

          <Section title="Inputs" caption="44px tall, 6px radius, calm focus">
            <div className="grid max-w-form grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <Label htmlFor="facility">Facility name</Label>
                <Input id="facility" placeholder="Springfield Water District" />
                <HelperText>The name as it should appear on the RFP cover page.</HelperText>
              </div>
              <div>
                <Label htmlFor="flow">Average daily flow (MGD)</Label>
                <Input id="flow" type="number" placeholder="12.4" />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="notes">Additional context</Label>
                <Textarea id="notes" placeholder="Anything we should know about this contract." />
              </div>
            </div>
          </Section>

          <Section title="Cards" caption="A surface, not a labeled box">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <Card>
                <CardBody>
                  <p className="text-numerical text-ink num">12</p>
                  <p className="text-caption uppercase tracking-wide text-ink-muted">Active contracts</p>
                </CardBody>
              </Card>
              <Card>
                <CardBody>
                  <p className="text-numerical text-ink num">28</p>
                  <p className="text-caption uppercase tracking-wide text-ink-muted">Chemicals tracked</p>
                </CardBody>
              </Card>
              <Card>
                <CardBody>
                  <p className="text-numerical text-ink num">62</p>
                  <p className="text-caption uppercase tracking-wide text-ink-muted">Portfolio risk score</p>
                </CardBody>
              </Card>
            </div>

            <div className="mt-3">
              <Card interactive>
                <div className="flex items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-title-3 text-ink">Aluminum sulfate · Drinking water</p>
                    <p className="text-body text-ink-muted">Bids close in 14 days. 6 NSF60 suppliers shortlisted.</p>
                  </div>
                  <ArrowRight className="h-2 w-2 text-ink-muted" strokeWidth={1.5} />
                </div>
              </Card>
            </div>
          </Section>

          <Section title="Tables" caption="Borderless, hairline row separators">
            <Card>
              <Table>
                <Thead>
                  <Tr>
                    <Th>Supplier</Th>
                    <Th>Origin</Th>
                    <Th className="text-right">$ / kg active</Th>
                    <Th className="text-right">Risk</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr className="border-l-[2px] border-l-accent">
                    <Td className="pl-2">
                      <p className="text-body-lg font-medium text-ink">Chemtrade Solutions</p>
                      <p className="text-caption text-ink-muted">$0.412 normalized · 50% solution</p>
                    </Td>
                    <Td className="text-ink-muted">Domestic</Td>
                    <Td className="text-right num">$0.412</Td>
                    <Td className="text-right">
                      <RiskDot band="Low" />
                    </Td>
                  </Tr>
                  <Tr>
                    <Td>
                      <p className="text-body-lg font-medium text-ink">USALCO</p>
                      <p className="text-caption text-ink-muted">$0.428 normalized · 49% solution</p>
                    </Td>
                    <Td className="text-ink-muted">Domestic</Td>
                    <Td className="text-right num">$0.428</Td>
                    <Td className="text-right">
                      <RiskDot band="Low" />
                    </Td>
                  </Tr>
                  <Tr>
                    <Td>
                      <p className="text-body-lg font-medium text-ink">Southern Ionics</p>
                      <p className="text-caption text-ink-muted">$0.467 normalized · 48% solution</p>
                    </Td>
                    <Td className="text-ink-muted">Domestic</Td>
                    <Td className="text-right num">$0.467</Td>
                    <Td className="text-right">
                      <RiskDot band="Moderate-Low" />
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </Card>
            <p className="mt-1 text-caption text-ink-muted">
              The recommended bid carries a 2px blue left border. No badges. No "RECOMMENDED" labels.
            </p>
          </Section>

          <Section title="Risk dots" caption="The only place color signals status">
            <div className="flex items-center gap-3 text-body">
              <span className="flex items-center gap-1">
                <RiskDot band="Low" /> Low
              </span>
              <span className="flex items-center gap-1">
                <RiskDot band="Moderate-Low" /> Moderate-Low
              </span>
              <span className="flex items-center gap-1">
                <RiskDot band="Moderate" /> Moderate
              </span>
              <span className="flex items-center gap-1">
                <RiskDot band="Moderate-High" /> Moderate-High
              </span>
              <span className="flex items-center gap-1">
                <RiskDot band="High" /> High
              </span>
            </div>
          </Section>

          <Section title="Modal" caption="No header bar, the title is just the first content element">
            <Modal>
              <ModalTrigger asChild>
                <Button variant="secondary">Open modal</Button>
              </ModalTrigger>
              <ModalContent>
                <ModalTitle>Award contract to Chemtrade Solutions</ModalTitle>
                <ModalDescription>
                  Generates a board-ready memo and locks the bid evaluation. This action can be reversed before
                  the memo is sent to the procurement office.
                </ModalDescription>
                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="tertiary">Cancel</Button>
                  <Button variant="primary">Generate memo</Button>
                </div>
              </ModalContent>
            </Modal>
          </Section>

          <Section title="Empty states" caption="One quiet line, one tertiary action">
            <Card>
              <EmptyState message="No bids submitted yet." action={<Button variant="tertiary">Upload bids</Button>} />
            </Card>
          </Section>

          <Section title="Iconography" caption="Lucide, stroke-width 1.5, never the default 2">
            <div className="flex items-center gap-3 text-ink">
              <FileText className="h-3 w-3" strokeWidth={1.5} />
              <ShieldCheck className="h-3 w-3" strokeWidth={1.5} />
              <Sparkles className="h-3 w-3" strokeWidth={1.5} />
              <ArrowRight className="h-3 w-3" strokeWidth={1.5} />
            </div>
          </Section>

          <Section title="Motion" caption="200ms ease-out on hover, 300ms on transitions, never bounce">
            <div className="flex flex-wrap gap-2">
              <button className="rounded-pill bg-bg-subtle px-3 py-1 text-body text-ink transition-colors duration-quick ease-out hover:bg-accent-muted">
                Hover me
              </button>
              <Card interactive className="cursor-pointer">
                <p className="text-body text-ink">Hover for raise</p>
              </Card>
            </div>
          </Section>

          <Section title="Layout" caption="Top nav only, no sidebars">
            <ul className="space-y-1 text-body text-ink-muted">
              <li>Content max width: 1080px (1280px on data-dense pages)</li>
              <li>Form max width: 720px (RFP Builder)</li>
              <li>Prose max width: 640px (Knowledge Q&A response)</li>
              <li>Vertical rhythm: 8 / 16 / 24 / 32 / 48 / 64 / 96 / 128 — never arbitrary</li>
            </ul>
            <p className="mt-2 text-body-lg text-ink-muted">
              Return to <Link href="/" className="text-accent hover:underline">the home page</Link>.
            </p>
          </Section>
        </div>
      </main>
    </>
  );
}

function Section({ title, caption, children }: { title: string; caption?: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-border-subtle py-5 first:border-t-0 first:pt-0">
      <div className="mb-3">
        <h2 className="text-title-2 text-ink">{title}</h2>
        {caption ? <p className="mt-half text-body text-ink-muted">{caption}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Specimen({ sample, role, className }: { sample: string; role: string; className?: string }) {
  return (
    <div className="flex items-baseline gap-3">
      <div className={className}>{sample}</div>
      <span className="text-caption uppercase tracking-wide text-ink-muted whitespace-nowrap">{role}</span>
    </div>
  );
}

function Swatch({ name, hex }: { name: string; hex: string }) {
  return (
    <div className="space-y-1">
      <div
        className="h-7 w-full rounded-md border border-border-subtle"
        style={{ background: hex }}
        aria-label={`${name} ${hex}`}
      />
      <p className="text-caption text-ink num">{hex}</p>
      <p className="text-caption text-ink-muted">{name}</p>
    </div>
  );
}
