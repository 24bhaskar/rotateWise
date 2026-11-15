import { ConfidencePanel } from "../components/ConfidencePanel";
import { PriorityPicker } from "../components/PriorityPicker";
import { StrategyCard } from "../components/StrategyCard";
import { ErrorNote, Loading, Pager, StepHeader } from "../components/ui";
import { useCounty, useStateData } from "../lib/data";
import { criterionWeights, rank, score } from "../lib/scoring";
import { useAppParams } from "../lib/url";

export function Options() {
  const { fips, sliders, setSlider, temp, rain } = useAppParams();
  const { data: state, error: e1 } = useStateData();
  const { data: c, error: e2 } = useCounty(fips);
  if (e1 || e2) return <ErrorNote message={(e1 ?? e2)!} />;
  if (!state || !c) return <Loading />;

  const { weights, note } = criterionWeights(sliders, c.rotation.excluded);
  const scores = score(c.rotation.criteria, weights);
  const order = rank(scores);
  const cell = c.scenario.find((x) => x.t === temp && x.r === rain);
  const scen = cell && (temp !== 0 || rain !== 0) ? { corn: cell.corn, soybean: cell.soybean } : null;

  return (
    <div className="wrap page">
      <StepHeader step="Step 3 of 4" title="Your options"
                  lede="Tell us what matters most. We rank three rotations by how well they fit your priorities and your county's weather." />

      <section aria-labelledby="prio" style={{ marginBottom: "var(--s-6)" }}>
        <h2 id="prio" style={{ fontSize: "1.4rem" }}>What matters most to you?</h2>
        <PriorityPicker value={sliders} onChange={setSlider} />
        {note && <p className="small muted" style={{ marginTop: 8 }}>{note}</p>}
      </section>

      <section aria-labelledby="ranked" className="stack">
        <h2 id="ranked" style={{ fontSize: "1.4rem" }}>Ranked for {c.name} County</h2>
        <p className="small muted" style={{ marginTop: 4 }}>The ranking is a transparent score from the model's risky months, the crop calendar,
          county rain records and published studies. It is not a yield forecast for each option.</p>
        {order.map((k, i) => (
          <StrategyCard key={k} card={c.rotation.cards[k]} rank={i + 1} score={scores[k]} state={state} top={i === 0} scenario={scen} raw={c.rotation.raw} />
        ))}
      </section>

      <div style={{ marginTop: "var(--s-6)" }}><ConfidencePanel county={c} sliders={sliders} /></div>

      <Pager back={{ to: "/risks", label: "What hurts yields" }} next={{ to: "/next", label: "Prepare to talk it over" }} />
    </div>
  );
}
