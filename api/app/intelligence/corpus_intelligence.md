# Water Treatment Chemical Market Intelligence

Compiled from a complete read of all 46 EPA Water Treatment Chemical Supply Chain Profiles
(December 2022 series, EPA 817-F-22 -010 through -056). Used by the platform's commercial engine
as a structured prior for risk scoring, RFP generation, and bid evaluation.

## Corpus inventory

46 chemicals across 9 functional categories used in U.S. drinking water and wastewater treatment.

| Category | Chemicals |
|---|---|
| Aluminum coagulants | Aluminum Hydroxide, Aluminum Sulfate, Bauxite (precursor), Polyaluminum Chloride |
| Iron coagulants | Ferric Chloride, Ferric Sulfate, Ferrous Chloride, Ferrous Sulfate |
| Chlorine / disinfection | Chlorine, Sodium Hypochlorite, Calcium Hypochlorite, Sodium Chlorite, Sodium Chlorate |
| Other oxidants | Hydrogen Peroxide, Potassium Permanganate, Sulfur Dioxide |
| pH / alkalinity | Calcium Carbonate, Calcium Hydroxide, Calcium Oxide, Sodium Carbonate, Sodium Hydroxide, Potassium Hydroxide, Carbon Dioxide |
| Acids | Hydrochloric Acid, Sulfuric Acid, Phosphoric Acid, Citric Acid, Fluorosilicic Acid |
| Phosphate corrosion control | Disodium Phosphate, Monosodium Phosphate, Sodium Salts of Polyphosphate, Zinc Orthophosphate, Phosphate Rock (precursor) |
| Polymer precursors / coagulant aids | Acrylamide, DADMAC, Sodium Silicate, Silica |
| Ammonia / chloramines | Anhydrous Ammonia, Ammonium Hydroxide |
| Industrial gases / atmospheric | Oxygen |
| Critical minerals (precursors) | Sodium Chloride (NaCl), Potassium Chloride (KCl), Manganese, Zinc, Sulfur, Ilmenite |

Direct-use water treatment chemicals: 33. Precursors / feedstocks: 13.

## Risk distribution at-a-glance (EPA 2022 ratings)

| Composite rating | Count | Notable members |
|---|---|---|
| Low | 24 | Aluminum Sulfate, Sulfuric Acid, all lime products, Sodium Chloride, Hydrogen Peroxide, Potassium Permanganate, Anhydrous Ammonia |
| Moderate-Low | 16 | Polyaluminum Chloride, Ferric Chloride, Ferric Sulfate, Bauxite, Soda Ash, CO2, O2, Acrylamide, HCl, Sulfur Dioxide, Sodium Silicate, Citric Acid, Phosphate Rock, MSP, Fluorosilicic Acid, Zinc Orthophosphate |
| Moderate | 0 | — |
| Moderate-High | 5 | Sodium Hydroxide, Sodium Hypochlorite, Chlorine, Disodium Phosphate, DADMAC, Phosphoric Acid |
| High | 0 | — |

Read-through: the EPA composite is multiplicative (Criticality × Likelihood × Vulnerability),
which dampens the rating when *any one* dimension is Low. Several "Low" composite chemicals
mask very high underlying criticality (e.g., HCl, Sulfuric Acid, Sodium Chloride). The platform
preserves the three sub-ratings separately so buyers can re-weight.

## Cross-cutting structural patterns

These patterns recur across the corpus and should be encoded as first-class signals in the platform.

### 1. Chlor-alkali co-production binds 10+ chemicals
Chlorine, sodium hydroxide, and hydrogen are co-produced in fixed stoichiometry. Demand for any
one of these (or downstream PVC, propylene oxide, etc.) shifts the supply curve for *all* others.
Winter Storm Uri (Feb 2021) knocked out ~28% of U.S. chlor-alkali capacity in a single event.
HCl is overwhelmingly a byproduct (>90%) of chlorinated organics manufacturing — its supply
collapses when downstream solvent/PVC demand collapses (2011 post-recession, 2020 COVID).

### 2. Imported bauxite is the single chokepoint for the entire aluminum coagulant family
Aluminum Sulfate, Polyaluminum Chloride, and Aluminum Hydroxide all share the same upstream
vulnerability — U.S. domestic bauxite production is negligible (<5% of consumption).
~5,100 M kg imported in 2019, primarily from Jamaica + Brazil. A bauxite price shock cascades
through the entire alum/PAC supply.

### 3. Iron salts are byproducts of steel pickling
All four iron salts (ferric chloride, ferric sulfate, ferrous chloride, ferrous sulfate) are
byproducts of spent-pickling-liquor processing or scrap iron + acid. Their availability is
*inverse* to steel industry health: economic slowdowns and pickling-liquor recycling reduce
supply. The 2020-2021 ferric/ferrous chloride shortage was driven by exactly this dynamic.

### 4. Phosphate value chain is tightly captive to fertilizer
Phosphate rock → Phosphoric acid → MSP/DSP/STPP/SHMP/ZnOP/FSA. ~95% of phosphate rock is
captively consumed by fertilizer producers (Mosaic ~12.8 B kg in 2020 captive). Water utilities
buy from the *non-fertilizer* fraction, so phosphate-derivative pricing rides ag cycles.
LFP battery demand is emerging as a new competing pull on phosphate.

### 5. Ammonia chain is anchored to natural gas
~75-80% of global ammonia is steam-methane-reformed; gas is ~70% of variable cost.
NH3 → +H2O → NH4OH → +Cl2 → chloramines. EIA Henry Hub spot price is the master signal for
chloramine-using utilities. ~88% of NH3 consumption is fertilizer; water is <2%.

### 6. Polymer precursor chain (acrylamide, DADMAC) is Gulf Coast petrochem
Acrylonitrile (acrylamide feedstock) and allyl chloride (DADMAC feedstock) are propylene
derivatives. SNF Holding dominates both: ~48% world polyacrylamide, ~85% domestic DADMAC.
Both 2021 hurricane (Ida) and winter storm (Uri) events caused force majeure declarations.

### 7. Industrial gases (CO2, O2) are local distribution markets, not bulk trade
Pipeline / cylinder / cryo-trailer distribution dominates; international trade is minimal.
The Big 4 (Linde, Air Liquide/Praxair, Air Products, Matheson) set merchant prices.
Florida is a recurring vulnerability hotspot (CO2 plant closures, summer 2021 LOX shortage
during COVID hospitalization surge).

### 8. Critical-mineral imports introduce country risk
- **Manganese**: 100% import-reliant since 1973; primary import partner Gabon.
- **Potash (KCl)**: ~95% imports, dominantly Saskatchewan; 178% global price spike Apr 2021–Apr 2022 tied to Russia/Belarus disruptions.
- **Bauxite**: <5% domestic; Jamaica + Brazil dominant.
- **Phosphate rock (non-fertilizer fraction)**: rising imports from Peru, Morocco; Mosaic 2020 DOC petition vs. Russia/Morocco shifted prices.

### 9. Antidumping/countervailing duties create import-pricing cliffs
- Calcium hypochlorite from China: +65.85% CVD on top of 25% Section 301 (effective ~95% duty).
- Potassium permanganate from China: +128.94% AD on top of 25% Section 301.
- These divert sourcing entirely to India for both chemicals — single-country import dependency.

### 10. HS-code aggregation is the dominant trade-data quality issue
Multiple water-treatment chemicals share aggregated HTS codes that mix in non-water-sector products:
- 2828.90 lumps NaOCl, Ca(OCl)2, NaClO2 (and various hypobromites).
- 2827.39.55 lumps iron chlorides with tin/barium/cobalt/zinc chlorides.
- 2811.19 (Inorganic Acids NES) buries fluorosilicic acid with other niche acids.
- 2833.29 lumps iron sulfates with other metal sulfates.
- 2835.22 lumps MSP and DSP together.

**Implication**: USITC DataWeb queries always need triangulation against producer disclosures
or paid sources to disaggregate. The Risk Monitor should flag any pricing assertion that comes
from a single coarse HTS code as low-confidence.

### 11. Single-domestic-producer concentration in 4+ chemicals
- Potassium Permanganate: Carus Corporation (Illinois) — sole U.S. manufacturer since 1998.
- Calcium Hypochlorite: only 2 U.S. sites (TN, WV) — both chlor-alkali co-located.
- Sodium Chlorite: 3 U.S. sites (UT, NE, IL) — OxyChem-dominated with full CBI claim.
- Acrylamide / DADMAC: SNF Holding ~48% world, ~85% domestic respectively.

### 12. CBI redaction in TSCA CDR limits transparency for organics
Acrylamide, DADMAC, citric acid, calcium hypochlorite, sodium chlorite, ZnOP all have
suppressed production data due to Confidential Business Information claims. This is a
structural data gap that buy-side pricing intelligence (order-level signals from procurement
tenders, vendor SDS revisions, FOIA pulls) can fill.

### 13. NSF/ANSI Standard 60 certified-supplier counts vary 50× across the corpus
Supplier-pool depth is a leading indicator of buy-side leverage.

| Chemical | NSF60 certified suppliers (2021) |
|---|---|
| Sodium Hydroxide | 224 |
| Polyaluminum Chloride | 140 |
| Aluminum Sulfate | 92 |
| Ferric Chloride | 88 |
| Ferric Sulfate | 63 |
| Ammonium Hydroxide | 52 |
| Sodium Carbonate | 39 |
| Anhydrous Ammonia | 36 |
| Carbon Dioxide | 34 |
| Potassium Hydroxide | 34 |
| Oxygen | 27 |
| Calcium Hydroxide | 26 |
| Ferrous Chloride | 17 |
| Calcium Hypochlorite | 14 |
| Calcium Oxide | 14 |
| Ferrous Sulfate | 5 |

The platform uses this count as a first-pass procurement-leverage score: <20 = concentrated
market, expect supplier pricing power; >50 = competitive market, buyer can play suppliers off.

### 14. Shelf life dictates inventory & forward-buy strategy
| Range | Chemicals | Procurement implication |
|---|---|---|
| < 3 months | Fluorosilicic Acid (1mo), Sodium Hypochlorite (1mo), Calcium Oxide (3mo) | JIT only; no strategic stockpiling; inventory <30 days; freight resilience critical |
| 6–12 months | Chlorine, Acrylamide, DADMAC, Sodium Carbonate, Calcium Hydroxide | Quarterly rebid feasible; 60-90 day inventory |
| 12–24 months | Most acids, NaOH, all phosphates, KOH, Sodium Chlorite | Annual contracts standard |
| 24+ months | Sulfuric Acid, NH4OH, NH3, Hydrogen Peroxide, all minerals | Multi-year contracts and forward inventory feasible |

### 15. Documented disruption events 2020-2022 cluster on three triggers
- **COVID-19** (2020-2021): demand collapse for refinery byproducts (sulfur), ethanol shutdown
  hitting CO2, freight constraints, force majeure cascade across Gulf Coast petrochem.
- **Winter Storm Uri** (Feb 2021): ~28% chlor-alkali capacity offline; affected chlorine,
  NaOH, NaOCl, Ca(OCl)2 supply for months.
- **Hurricane Ida** (Aug 2021): Gulf Coast acrylonitrile and allyl chloride force majeure
  → polymer precursor shortage. Closed largest U.S. KOH facility temporarily.
- **2021 LOX (medical oxygen) shortage**: hospitalization surge spiked demand; HazMat-driver
  shortage compounded; Florida especially affected.
- **Permanent capacity reductions in 2021**: Olin Alabama, Occidental Niagara Falls — net
  reduction in U.S. chlor-alkali nameplate capacity.

## How the platform uses this intelligence

1. **Risk Monitor** layers daily NOAA hurricane tracking, EIA gas/petroleum prices, BLS PPI,
   and USITC DataWeb monthly trade onto the static EPA risk priors. A 2-σ swing in any
   leading indicator generates a watch-level alert; a 3-σ swing generates a warning.

2. **RFP Builder** scales resilience clauses to risk rating: Low-rated chemicals get standard
   AWWA boilerplate; Moderate-Low and above get force-majeure carve-outs, dual-source
   requirements, and inventory-buffer commitments. Uses NSF60 supplier counts to size the
   shortlist.

3. **Bid Evaluator** normalizes supplier prices to $/kg of *active ingredient* (e.g., adjusts
   for delivered concentration, handles HTS-aggregation distortions for imported product),
   then risk-adjusts the score using the EPA composite + the platform's dynamic delta.

4. **Knowledge Q&A** grounds answers in the EPA fact sheet via pgvector RAG. Citations cite
   the section + page number from the original EPA PDF, hyperlinked to the saved corpus copy.

5. **Memo generator** draws cross-references to the EPA fact sheet directly when justifying
   risk-weighted scoring decisions in board-ready award memos. Municipal memos use
   AWWA-style language; industrial memos use ESG/risk-register conventions.

## Maintenance

- The 2024 TSCA CDR cycle (reporting year 2023) will refresh production volumes — re-run the
  ingestion agent on EPA's next fact sheet release, expected late 2024 or 2025.
- Antidumping/countervailing orders change quarterly. Federal Register alerts on the docket
  numbers in `price_sources.json` keep this current.
- Add new chemicals by dropping a fact sheet PDF into the corpus directory and running
  `python -m ingestion.run --only "<chemical name>"`.
