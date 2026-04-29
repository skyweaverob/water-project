"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Nav } from "@/components/nav";
import { Button } from "@/components/ui/button";
import { HelperText, Input, Label } from "@/components/ui/input";

/**
 * Single-column RFP form, max-width 720px, progressive disclosure.
 * Each section appears as the user completes the previous one — no accordions, no tabs.
 */
export default function NewRfpPage() {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [facility, setFacility] = useState({ name: "", sector: "drinking_water", flow_mgd: "", state: "" });
  const [chemical, setChemical] = useState("");
  const [contract, setContract] = useState({ quantity: "", term_months: "24", delivery_days: "14" });

  const canStep2 = facility.name.trim().length > 1 && facility.sector;
  const canStep3 = chemical.trim().length > 1;
  const canSubmit = contract.quantity && parseInt(contract.term_months, 10) > 0;

  async function submit() {
    // Wire to /facilities then /rfps in production. Here we route to the index for the demo.
    router.push("/rfps");
  }

  return (
    <>
      <Nav />
      <main className="pt-nav">
        <div className="mx-auto max-w-form px-3 py-6">
          <header className="mb-5">
            <h1 className="text-title-1 text-ink">New RFP</h1>
            <p className="mt-1 text-body-lg text-ink-muted">
              Tell us about the facility and the chemical. We'll draft a procurement-ready
              package — specs, resilience clauses scaled to risk, evaluation weights, and a
              suggested timeline.
            </p>
          </header>

          <section className="space-y-3">
            <h2 className="text-title-3 text-ink">Facility</h2>
            <div>
              <Label htmlFor="fname">Facility name</Label>
              <Input
                id="fname"
                value={facility.name}
                onChange={(e) => setFacility({ ...facility, name: e.target.value })}
                placeholder="Springfield Water District"
              />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <Label htmlFor="sector">Sector</Label>
                <select
                  id="sector"
                  className="h-[44px] w-full rounded-sm border border-border bg-white px-2 text-body text-ink focus:border-accent focus:shadow-focus focus:outline-none"
                  value={facility.sector}
                  onChange={(e) => setFacility({ ...facility, sector: e.target.value })}
                >
                  <option value="drinking_water">Drinking water</option>
                  <option value="wastewater">Wastewater</option>
                  <option value="industrial_pretreatment">Industrial pretreatment</option>
                </select>
              </div>
              <div>
                <Label htmlFor="flow">Average daily flow (MGD)</Label>
                <Input
                  id="flow"
                  type="number"
                  value={facility.flow_mgd}
                  onChange={(e) => setFacility({ ...facility, flow_mgd: e.target.value })}
                  placeholder="12.4"
                />
              </div>
            </div>
            {step === 1 && (
              <div className="pt-2">
                <Button variant="primary" disabled={!canStep2} onClick={() => setStep(2)}>
                  Continue
                </Button>
              </div>
            )}
          </section>

          {step >= 2 && (
            <section className="mt-6 space-y-3 pt-5 border-t border-border-subtle">
              <h2 className="text-title-3 text-ink">Chemical</h2>
              <div>
                <Label htmlFor="chem">Chemical name</Label>
                <Input
                  id="chem"
                  value={chemical}
                  onChange={(e) => setChemical(e.target.value)}
                  placeholder="Aluminum Sulfate"
                />
                <HelperText>The platform supports all 46 EPA-profiled chemicals.</HelperText>
              </div>
              {step === 2 && (
                <div className="pt-2">
                  <Button variant="primary" disabled={!canStep3} onClick={() => setStep(3)}>
                    Continue
                  </Button>
                </div>
              )}
            </section>
          )}

          {step >= 3 && (
            <section className="mt-6 space-y-3 pt-5 border-t border-border-subtle">
              <h2 className="text-title-3 text-ink">Contract terms</h2>
              <div>
                <Label htmlFor="qty">Estimated annual demand (kg)</Label>
                <Input
                  id="qty"
                  type="number"
                  value={contract.quantity}
                  onChange={(e) => setContract({ ...contract, quantity: e.target.value })}
                  placeholder="2,500,000"
                />
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <Label htmlFor="term">Term (months)</Label>
                  <Input
                    id="term"
                    type="number"
                    value={contract.term_months}
                    onChange={(e) => setContract({ ...contract, term_months: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="dwin">Delivery window (days)</Label>
                  <Input
                    id="dwin"
                    type="number"
                    value={contract.delivery_days}
                    onChange={(e) => setContract({ ...contract, delivery_days: e.target.value })}
                  />
                </div>
              </div>
              <div className="pt-2">
                <Button variant="primary" disabled={!canSubmit} onClick={submit}>
                  Generate RFP
                </Button>
              </div>
            </section>
          )}
        </div>
      </main>
    </>
  );
}
