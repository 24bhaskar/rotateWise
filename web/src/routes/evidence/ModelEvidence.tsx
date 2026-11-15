import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Term } from "../../components/Term";
import { ErrorNote, Loading } from "../../components/ui";
import { useEvidence } from "../../lib/data";
import { num, share, signedPct } from "../../lib/format";

type Crop = "corn" | "soy";
const MODEL_LABEL: Record<string, string> = { M0: "Trend only (no weather)", M1: "Same as last year", M2: "Simple 3-feature model", selected: "RotateWise model (GAM)" };
const ci = (v?: number[]) => (v ? `${num(v[0])}–${num(v[1])}` : "–");

export function ModelEvidence() {
  const { data: s, error } = useEvidence();
  const [crop, setCrop] = useState<Crop>("corn");
  if (error) return <ErrorNote message={error} />;
  if (!s) return <Loading />;
  const m = s.evidence.metrics[crop];
  const t = m.test_expanding_trend;
  const sel = m.selected_model;
  const rows = (["M0", "M1", "M2", "selected"] as const).map((k) => ({
    k, dev: m.dev_cv[k === "selected" ? sel : k], test: t[k],
  }));
  const by = s.evidence.by_year[crop];
  const years = [...new Set([...by.dev.map((d) => d.year), ...by.test.map((d) => d.year)])].sort();
  const lineData = years.map((y) => {
    const pick = (id: string) => (by.dev.find((d) => d.year === y && d.model_id === id) ?? by.test.find((d) => d.year === y && d.model === id))?.rmse;
    return { year: y, trend: pick("M0"), model: pick("selected"), simple: pick("M2") };
  });
  const imp = [...s.evidence.shap[crop].importance].sort((a, b) => b.mean_abs - a.mean_abs);
  const y25 = t.year_2025_only;

  return (
    <div className="stack">
      <div className="seg" role="group" aria-label="Crop">
        {(["corn", "soy"] as Crop[]).map((c) => <button key={c} type="button" aria-pressed={crop === c} onClick={() => setCrop(c)}>{c === "corn" ? "Corn" : "Soybean"}</button>)}
      </div>

      <div className="callout good">
        <p><strong>In short:</strong> on the six held-back years (2020-2025), the model's typical error was {num(t.selected.rmse)} points
          of trend yield, against {num(t.M0.rmse)} for simply assuming "a normal year" — about {share(t.selected.skill_vs_m0 ?? 0)} better.
          A real but modest gain: it mostly captures good vs bad <em>years</em>, less so which counties do better within a year.</p>
      </div>

      <section className="card">
        <h2 className="h3">Compared with simple baselines</h2>
        <p className="small muted">Error = typical distance between predicted and actual <Term k="anomaly">yield anomaly</Term>, in percentage points
          (lower is better). Ranges are 90% bootstrap intervals over years. Model chosen by a rule written before testing.</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Approach</th><th className="num">Training years 2000-19 (cross-validated)</th><th className="num">Held-back years 2020-25</th><th className="num">Range</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.k} className={r.k === "selected" ? "highlight" : undefined}>
                  <td>{MODEL_LABEL[r.k]}</td>
                  <td className="num">{num(r.dev?.rmse)}</td>
                  <td className="num">{num(r.test.rmse)}</td>
                  <td className="num">{ci(r.test.boot?.rmse)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {y25 && <p className="small" style={{ marginTop: 12 }}><strong>2025, the cleanest test:</strong> never seen before the final run. Statewide the model
          predicted {signedPct(y25.selected.state_pred)} vs {signedPct(y25.selected.state_actual)} actual.</p>}
        <p className="small muted">Selection: {m.selection_notes.reason}.</p>
      </section>

      <section className="card">
        <h2 className="h3">Error year by year</h2>
        <div className="chart">
          <ResponsiveContainer>
            <LineChart data={lineData} margin={{ top: 10, right: 16, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "var(--ink-3)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--ink-3)", fontSize: 12 }} />
              <Tooltip formatter={(v) => num(Number(v))} contentStyle={{ borderRadius: 10 }} />
              <Legend />
              <Line dataKey="trend" name="Trend only" stroke="var(--c-base)" strokeDasharray="4 4" dot={false} />
              <Line dataKey="simple" name="Simple model" stroke="var(--c-b)" dot={false} />
              <Line dataKey="model" name="RotateWise" stroke="var(--c-model)" strokeWidth={3} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="chart-cap">2000-2019: each year predicted by a model that never saw it. 2020-2025: the one-time locked test.
          Note: 2020-2024 were scored once by an earlier prototype before this protocol, so 2025 is the only fully unseen year.</p>
      </section>

      <div className="grid grid-2">
        <section className="card">
          <h2 className="h3">What the model pays attention to</h2>
          <div className="chart" style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={imp} layout="vertical" margin={{ left: 10, right: 16 }}>
                <XAxis type="number" tick={{ fill: "var(--ink-3)", fontSize: 12 }} />
                <YAxis type="category" dataKey="label" width={170} tick={{ fill: "var(--ink-2)", fontSize: 12 }} />
                <Tooltip formatter={(v) => [num(Number(v), 2), "avg. effect (pts)"]} contentStyle={{ borderRadius: 10 }} />
                <Bar dataKey="mean_abs" fill="var(--c-model)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-cap">Average size of each feature's push on predictions (<Term k="SHAP">SHAP</Term>), all counties and years.</p>
        </section>
        <section className="card">
          <h2 className="h3">Honesty checks</h2>
          <ul>
            <li><strong>Shuffled weather:</strong> giving the model the wrong years' weather makes it no better than trend-only
              ({num(m.placebo.shuffled_rmse_mean)} vs {num(m.placebo.m0_rmse)}). It is learning from weather, not memorising.</li>
            <li><strong>Overfitting:</strong> training error {num(m.train_vs_cv_gap.train_rmse)} vs cross-validated {num(m.train_vs_cv_gap.cv_rmse)} — a small gap.</li>
            <li><strong>New places:</strong> holding out whole regions gives {num(m.spatial_block.rmse)}, close to the main result.</li>
            <li><strong>Soil-moisture data:</strong> removing NASA <Term k="root-zone wetness">root-zone wetness</Term> barely changes accuracy
              ({num(m.ablations["A1_without_gwetroot"])} vs {num(m.ablations["A1_reference_selected"])}); temperature and rain carry the model.</li>
            <li><strong>Uncertainty:</strong> the 90% <Term k="prediction interval">range</Term> is ±{num(m.intervals.conformal_90_halfwidth_pct, 0)} points
              and covered {share(t.selected.conformal_90_test_coverage ?? 0)} of test cases, but only {share(m.intervals.conformal_worst_year_coverage)} in
              the worst training year: extreme years are under-covered.</li>
          </ul>
        </section>
      </div>

      <details className="card">
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Every model we tried ({s.evidence.experiments.filter((e) => e.crop === crop).length})</summary>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table>
            <thead><tr><th>Model</th><th className="num">CV error</th><th className="num">Skill vs trend</th><th className="num">Train error</th></tr></thead>
            <tbody>
              {s.evidence.experiments.filter((e) => e.crop === crop).sort((a, b) => a.cv_rmse - b.cv_rmse).map((e) => (
                <tr key={e.model_id} className={e.selected ? "highlight" : undefined}>
                  <td>{e.model_id}{e.selected ? " (selected)" : ""}</td><td className="num">{num(e.cv_rmse, 2)}</td>
                  <td className="num">{e.skill_vs_m0 === null ? "–" : share(e.skill_vs_m0)}</td><td className="num">{num(e.train_rmse, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem", marginTop: 16 }}>{s.evidence.selection_rule}</pre>
      </details>
    </div>
  );
}
