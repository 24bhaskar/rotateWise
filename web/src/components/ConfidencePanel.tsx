import { Scale } from "lucide-react";
import { useMemo } from "react";
import { criterionWeights, rank, score, weightSensitivity } from "../lib/scoring";
import { STRATEGY_COLOR, STRATEGY_SHORT, share } from "../lib/format";
import type { CountyData, Sliders, StrategyId } from "../lib/types";

const order = (ids: StrategyId[]) => ids.map((k) => STRATEGY_SHORT[k].toLowerCase()).join(", then ");

/** How robust is the ranking? Priority mixes, crop timing, and the one expert rating. */
export function ConfidencePanel({ county, sliders }: { county: CountyData; sliders: Sliders }) {
  const rot = county.rotation;
  const sens = useMemo(() => weightSensitivity(rot.criteria, rot.excluded), [rot]);
  const { weights } = criterionWeights(sliders, rot.excluded);
  const base = rank(score(rot.criteria, weights));
  const shiftRank = (d: string) => rank(score(rot.calendar_shifts[d].criteria, weights));
  const later = shiftRank("14"), earlier = shiftRank("-14");
  const same = (a: StrategyId[]) => a.join() === base.join();
  const passes = Object.values(rot.rye_passes).map((c) => rank(score(c, weights)));
  const ids = Object.keys(sens) as StrategyId[];

  return (
    <section className="card" aria-labelledby="conf">
      <h2 id="conf" style={{ fontSize: "1.4rem", display: "flex", gap: 8, alignItems: "center" }}><Scale size={22} aria-hidden="true" /> How sure is this ranking?</h2>
      <p className="muted">We tried 2,000 different mixes of priorities. Here is how often each option came out on top:</p>
      <div style={{ display: "grid", gap: 8, marginBottom: "var(--s-4)" }}>
        {ids.map((k) => (
          <div key={k} style={{ display: "grid", gridTemplateColumns: "minmax(140px, 220px) 1fr 48px", gap: 10, alignItems: "center" }}>
            <span className="small" style={{ fontWeight: 600 }}>{STRATEGY_SHORT[k]}</span>
            <span className="scorebar" style={{ height: 14 }}><div style={{ width: `${Math.max(2, sens[k].shareFirst * 100)}%`, background: STRATEGY_COLOR[k] }} /></span>
            <span className="num small" style={{ textAlign: "right" }}>{share(sens[k].shareFirst)}</span>
          </div>
        ))}
      </div>
      <ul>
        <li><strong>Crop timing:</strong> {same(later) && same(earlier)
          ? "planting and harvest 2 weeks earlier or later than usual would not change the order."
          : <>if crops go in and come out about 2 weeks <strong>{same(later) ? "earlier" : "later"}</strong> than usual, the order becomes{" "}
              {order(same(later) ? earlier : later)}. Timing varies by year and field, so treat close calls as close.</>}</li>
        <li><strong>Expert estimate:</strong> {passes.every((p) => p.join() === base.join())
          ? "changing our estimate of extra field passes for rye by one either way does not change the order."
          : "changing our estimate of extra field passes for rye by one changes the order; this needs local review."}</li>
        {Object.keys(rot.excluded).length > 0 && (
          <li><strong>Not scored yet:</strong> water use and soil-building value need crop data we could not yet confirm from published
            sources, so “Conserve water” currently counts through heat-month exposure, and “Soil health” through soil cover.</li>
        )}
      </ul>
    </section>
  );
}
