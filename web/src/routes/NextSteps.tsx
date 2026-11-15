import { Printer, Share2 } from "lucide-react";
import { useState } from "react";
import { ErrorNote, Loading, Pager, StepHeader } from "../components/ui";
import { useCounty, useStateData } from "../lib/data";
import { DRAG_PLAIN, STRATEGY_SHORT, share } from "../lib/format";
import { criterionWeights, rank, score } from "../lib/scoring";
import { SLIDER_KEYS } from "../lib/scoring";
import { useAppParams } from "../lib/url";

const SLIDER_LABEL = { water: "Conserve water", soil: "Soil health", income: "Income", labor: "Low labour" };

/** Turn a card's own gap/risk sentences into questions, without adding new claims. */
function asQuestion(s: string) {
  const t = s.replace(/\s*\((?:[^)]*S\d+[^)]*)\)\.?$/, "").replace(/\.$/, "");
  return `How does this apply to my farm: ${t.charAt(0).toLowerCase()}${t.slice(1)}?`;
}

export function NextSteps() {
  const { fips, sliders } = useAppParams();
  const { data: state, error: e1 } = useStateData();
  const { data: c, error: e2 } = useCounty(fips);
  const [copied, setCopied] = useState(false);
  if (e1 || e2) return <ErrorNote message={(e1 ?? e2)!} />;
  if (!state || !c) return <Loading />;

  const { weights } = criterionWeights(sliders, c.rotation.excluded);
  const scores = score(c.rotation.criteria, weights);
  const order = rank(scores);
  const topCard = c.rotation.cards[order[0]];
  const questions = [
    ...topCard.risks_needing_local_review.slice(0, 3).map(asQuestion),
    "Do my field's soil, drainage and slope change any of this?",
    "Are there cost-share programs or local markets that would affect these options?",
  ];

  return (
    <div className="wrap page">
      <StepHeader step="Step 4 of 4" title="Talk it over with someone who knows your fields"
                  lede="Print or share this one-page summary and bring it to your agronomist or county extension office." />

      <div className="btn-row no-print" style={{ marginBottom: "var(--s-5)" }}>
        <button type="button" className="btn btn-primary" onClick={() => window.print()}><Printer size={18} aria-hidden="true" /> Print or save as PDF</button>
        <button type="button" className="btn btn-ghost" onClick={() => navigator.clipboard?.writeText(window.location.href).then(() => setCopied(true))}>
          <Share2 size={18} aria-hidden="true" /> {copied ? "Link copied" : "Copy a link to these results"}
        </button>
      </div>

      <article className="card stack">
        <header>
          <p className="eyebrow">RotateWise summary · {c.name} County, Iowa</p>
          <h2 style={{ margin: 0 }}>Rotation options to discuss</h2>
        </header>
        <div className="grid grid-2">
          <div>
            <h3>Priorities used</h3>
            <ul>{SLIDER_KEYS.map((k) => <li key={k}>{SLIDER_LABEL[k]}: {sliders[k]} of 5</li>)}</ul>
          </div>
          <div>
            <h3>Ranking</h3>
            <ol>{order.map((k) => <li key={k}><strong>{STRATEGY_SHORT[k]}</strong> — fit {Math.round(scores[k] * 100)}/100</li>)}</ol>
          </div>
        </div>
        <div>
          <h3>What the weather record shows</h3>
          <p>Biggest weather drags on corn here: {c.drivers.corn.map((d) => DRAG_PLAIN[d.feature] ?? d.label).join("; ")}. Under corn → soybean
            the soil is bare about {share(c.rotation.raw.A.bare_fraction)} of the year.</p>
        </div>
        {order.map((k) => {
          const card = c.rotation.cards[k];
          return (
            <div key={k} style={{ breakInside: "avoid" }}>
              <h3>{STRATEGY_SHORT[k]}</h3>
              <p className="small"><strong>Why:</strong> {card.why_suggested}</p>
              <p className="small"><strong>Risks to review:</strong> {card.risks_needing_local_review.join(" ")}</p>
            </div>
          );
        })}
        <div className="callout good">
          <h3>Questions to ask</h3>
          <ol style={{ margin: 0 }}>{questions.map((q, i) => <li key={i}>{q}</li>)}</ol>
        </div>
        <p className="small muted">{state.meta.support_line} County-scale hindcast from NASA POWER and USDA data, not a forecast.
          Generated {new Date().toLocaleDateString()}.</p>
      </article>

      <Pager back={{ to: "/options", label: "Your options" }} next={{ to: "/evidence", label: "See the evidence" }} />
    </div>
  );
}
