import { AlertTriangle, CloudRain, Thermometer } from "lucide-react";
import { signedPct } from "../lib/format";
import type { CountyData, State } from "../lib/types";
import { useAppParams } from "../lib/url";
import { Term } from "./Term";

/** Precomputed what-if: past seasons replayed with warmer/cooler and wetter/drier weather. */
export function WhatIf({ county, state }: { county: CountyData; state: State }) {
  const { temp, rain, setWhatIf } = useAppParams();
  const temps = state.meta.temp_steps, rains = state.meta.rain_steps;
  const t = temps.includes(temp) ? temp : 0, r = rains.includes(rain) ? rain : 0;
  const cell = county.scenario.find((x) => x.t === t && x.r === r)!;
  const base = county.scenario.find((x) => x.t === 0 && x.r === 0)!;
  const dCorn = cell.corn - base.corn, dSoy = cell.soybean - base.soybean;
  const conf = state.conformal;
  const isBase = t === 0 && r === 0;
  const describe = () => {
    const parts = [];
    if (t !== 0) parts.push(`${Math.abs(t)} °C ${t > 0 ? "warmer" : "cooler"}`);
    if (r !== 0) parts.push(`${Math.abs(r)}% ${r > 0 ? "wetter" : "drier"}`);
    return parts.join(" and ");
  };
  const word = (d: number) => (Math.abs(d) < 0.25 ? "about the same" : d < 0 ? `${Math.abs(d).toFixed(1)}% lower` : `${d.toFixed(1)}% higher`);

  return (
    <div className="card">
      <h2 className="h3">What if summers change?</h2>
      <p className="muted">We replay all 26 past seasons with the weather nudged, and ask the model what yields would have looked like.</p>
      <div className="grid grid-2">
        <div>
          <label className="field-label" htmlFor="wi-t"><Thermometer size={16} style={{ display: "inline", verticalAlign: -3 }} aria-hidden="true" /> Temperature: {t > 0 ? "+" : ""}{t} °C</label>
          <input id="wi-t" className="range" type="range" min={0} max={temps.length - 1} step={1} value={temps.indexOf(t)}
                 aria-valuetext={`${t} degrees`} onChange={(e) => setWhatIf(temps[Number(e.target.value)], r)} />
          <div className="range-scale"><span>{temps[0]} °C</span><span>0</span><span>+{temps[temps.length - 1]} °C</span></div>
        </div>
        <div>
          <label className="field-label" htmlFor="wi-r"><CloudRain size={16} style={{ display: "inline", verticalAlign: -3 }} aria-hidden="true" /> Rainfall: {r > 0 ? "+" : ""}{r}%</label>
          <input id="wi-r" className="range" type="range" min={0} max={rains.length - 1} step={1} value={rains.indexOf(r)}
                 aria-valuetext={`${r} percent`} onChange={(e) => setWhatIf(t, rains[Number(e.target.value)])} />
          <div className="range-scale"><span>{rains[0]}%</span><span>0</span><span>+{rains[rains.length - 1]}%</span></div>
        </div>
      </div>
      <div className={`callout ${isBase ? "" : dCorn < -0.25 ? "warn" : "good"}`} style={{ marginTop: "var(--s-4)" }} aria-live="polite">
        {isBase
          ? <p>Move a slider to see how warmer, cooler, wetter or drier seasons would have changed yields here.</p>
          : <p>If past seasons had been <strong>{describe()}</strong>, the model says yields would have averaged{" "}
              {[["corn", dCorn], ["soybeans", dSoy]].map(([crop, d], i) => (
                <span key={crop as string}>{i > 0 && " and "}<strong>{word(d as number)}</strong> for {crop}</span>
              ))}
              {" "}compared with the real weather.</p>}
        <p className="small muted" style={{ margin: 0 }}>Single seasons vary a lot: a <Term k="prediction interval">90% range</Term> is
          about ±{Math.round(conf.corn.halfwidth_pct)} points for corn and ±{Math.round(conf.soy.halfwidth_pct)} for soybeans
          ({signedPct(cell.corn)} corn, {signedPct(cell.soybean)} soybean vs trend on average).</p>
      </div>
      {cell.clipped > 0 && (
        <p className="small" style={{ marginTop: 10, display: "flex", gap: 6 }}><AlertTriangle size={16} style={{ flex: "none", color: "var(--rust)" }} aria-hidden="true" />
          Some of these seasons go beyond the weather the model learned from, so the effect is capped there.</p>
      )}
      <p className="chart-cap">Likely an underestimate: soil moisture is not re-simulated, and the model already underpredicts extreme
        years like 2012. Only corn and soybeans are modelled.</p>
    </div>
  );
}
