import { CalendarRange } from "lucide-react";
import { CoverRibbon } from "../components/CoverRibbon";
import { MonthStrip } from "../components/MonthStrip";
import { Term } from "../components/Term";
import { ErrorNote, Loading, Pager, StepHeader } from "../components/ui";
import { WhatIf } from "../components/WhatIf";
import { useCounty, useStateData } from "../lib/data";
import { DRAG_PLAIN, MONTHS, MONTHS_LONG, share } from "../lib/format";
import { useAppParams } from "../lib/url";

export function Risks() {
  const { data: state, error: e1 } = useStateData();
  const { fips } = useAppParams();
  const { data: c, error: e2 } = useCounty(fips);
  if (e1 || e2) return <ErrorNote message={(e1 ?? e2)!} />;
  if (!state || !c) return <Loading />;

  const corn = state.stress.corn;
  const months = Object.keys(corn).map(Number).filter((m) => corn[m] > 0).sort((a, b) => corn[b] - corn[a]);
  const top = months[0];
  const drivers = c.drivers.corn.slice(0, 3);
  const bareA = c.rotation.raw.A.bare_fraction;

  return (
    <div className="wrap page">
      <StepHeader step="Step 2 of 4" title={`What hurts yields in ${c.name} County`}
                  lede={<>Across Iowa, the model found that <strong>{MONTHS_LONG[top - 1]} weather matters most for corn</strong> —
                    about {share(corn[top])} of its sensitivity — followed by {months.slice(1, 3).map((m) => MONTHS_LONG[m - 1]).join(" and ")}.</>} />

      <div className="grid grid-2">
        <div className="card">
          <h2 className="h3">Biggest weather drags here</h2>
          <p className="muted small">The conditions that most often pulled {c.name} County's corn below its <Term k="trend">trend</Term>,
            according to the model's <Term k="SHAP">explanations</Term>:</p>
          <ol style={{ paddingLeft: "1.2em", margin: 0 }}>
            {drivers.map((d) => (
              <li key={d.feature} style={{ marginBottom: 8 }}>
                <strong>{DRAG_PLAIN[d.feature] ?? d.label}</strong>
                <span className="muted small"> · {MONTHS[d.months[0] - 1]}{d.months.length > 1 ? `–${MONTHS[d.months[d.months.length - 1] - 1]}` : ""}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="card">
          <h2 className="h3">Bare soil in storm season</h2>
          <p>Under corn → soybean, the soil is bare about <strong>{share(bareA)} of the year</strong>, mostly late fall to spring —
            when much of this county's heavy rain falls. Bare soil is when erosion and nutrient loss happen.</p>
          <CoverRibbon cal={state.strategy_calendar} only={["A"]} />
        </div>
      </div>

      <section className="card" style={{ marginTop: "var(--s-5)" }}>
        <h2 style={{ fontSize: "1.4rem", display: "flex", gap: 8, alignItems: "center" }}><CalendarRange size={22} aria-hidden="true" /> Your risk calendar</h2>
        <p className="muted">How often each kind of weather trouble shows up in each month. Darker means more years.
          Includes <Term k="frost risk">frost</Term>, heat stress, dry spells, heavy rain and <Term k="water balance">water deficit</Term>.</p>
        <MonthStrip risk={c.risk} />
      </section>

      <section style={{ marginTop: "var(--s-5)" }}>
        <WhatIf county={c} state={state} />
      </section>

      <Pager back={{ to: "/field", label: "Your county" }} next={{ to: "/options", label: "Compare your options" }} />
    </div>
  );
}
