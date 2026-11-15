import { ExternalLink } from "lucide-react";
import { Term } from "../../components/Term";
import { ErrorNote, Loading } from "../../components/ui";
import { GLOSSARY } from "../../content/glossary";
import { useEvidence, useStateData } from "../../lib/data";

const STEPS = ["NASA POWER daily weather at 99 county centres", "Season summaries per county and year",
  "USDA yields → % above or below each county's trend", "Model learns weather → yield anomaly",
  "Risky months + crop calendar + cited studies", "Ranked rotation options"];

export function DataMethods() {
  const { data: s, error: e1 } = useStateData();
  const { data: ev, error: e2 } = useEvidence();
  if (e1 || e2) return <ErrorNote message={(e1 ?? e2)!} />;
  if (!s || !ev) return <Loading />;

  return (
    <div className="stack">
      <section className="card">
        <h2 className="h3">How the pieces fit</h2>
        <ol style={{ display: "grid", gap: 10, listStyle: "none", padding: 0, margin: 0 }}>
          {STEPS.map((t, i) => (
            <li key={i} style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <span className="rank" style={{ background: i < 4 ? "var(--crop)" : "var(--soil)", width: 32, height: 32, fontSize: "1rem" }}>{i + 1}</span>
              <span>{t}</span>
            </li>
          ))}
        </ol>
        <p className="chart-cap">Everything is put on one county × month grid. The model is a <Term k="hindcast">hindcast</Term>: it explains past
          seasons using weather known only after harvest.</p>
      </section>

      <section className="card">
        <h2 className="h3">Satellite, model or ground?</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Source</th><th>What it is</th><th>Detail</th><th>Limits</th></tr></thead>
            <tbody>
              <tr><td>NASA POWER</td><td><Term k="reanalysis">Reanalysis</Term> plus satellite inputs</td><td>~50 km, daily since 1981</td><td>Soil wetness is modelled; neighbouring counties share cells ({s.meta.power_cells} cells for 99 counties)</td></tr>
              <tr><td>NASA MODIS NDVI</td><td>Satellite greenness</td><td>250 m, every 16 days</td><td>Clouds; greenness is not yield</td></tr>
              <tr><td>NASA SMAP</td><td>Satellite soil moisture</td><td>~9 km, since 2015</td><td>Not used yet (needs an Earthdata login)</td></tr>
              <tr><td>Your soil probe or weather station</td><td>Ground measurement</td><td>One point</td><td>Most accurate there, covers nothing else</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2 className="h3">Sources</h2>
        <p className="small muted">Every reference was opened and summarised in our own words. None has been checked by a human expert yet.</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>What it supports</th><th>Source</th><th>Link check</th></tr></thead>
            <tbody>{ev.sources.map((r) => (
              <tr key={r.id} id={`src-${r.id}`}>
                <td>{r.id}</td><td className="small">{r.claim_supported}</td>
                <td className="small"><a href={r.url} target="_blank" rel="noreferrer">{r.title} <ExternalLink size={12} style={{ display: "inline" }} aria-hidden="true" /></a>
                  <br /><span className="muted">{r.publisher}, {r.year}</span></td>
                <td className="small">{r.status ?? "unchecked"}{r.checked ? ` · ${r.checked}` : ""}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <div className="grid grid-2">
        <section className="card">
          <h2 className="h3">Limits to keep in mind</h2>
          <ul>
            <li>Explains past seasons (hindcast); it does not forecast this year.</li>
            <li>County scale, not your field: soil, drainage and slope are information gaps.</li>
            <li>About 20 independent weather years to learn from and 6 to test: evidence, not proof.</li>
            <li>Insurance payouts are claims, not measured yield loss.</li>
            <li>Oats, red clover and rye are not modelled; their timing uses a corn/soybean proxy.</li>
            <li>Rotation scores are a transparent formula from cited sources and crop timing, not a yield forecast for each option.</li>
            <li>Water use and soil-building value are not scored until more crop facts are sourced.</li>
          </ul>
        </section>
        <section className="card">
          <h2 className="h3">How this was made</h2>
          <p className="small">Code, data processing and source summaries were written with an AI coding assistant (Claude Code, Anthropic) from the
            team's design; every number on this site is computed from the cited public datasets. Full disclosure and the human-review log are in the
            project README.</p>
          <h2 className="h3" style={{ marginTop: 16 }}>Glossary</h2>
          <dl className="small" style={{ margin: 0 }}>
            {Object.entries(GLOSSARY).map(([k, v]) => <div key={k} style={{ marginBottom: 8 }}><dt style={{ fontWeight: 700, textTransform: "capitalize" }}>{k}</dt><dd style={{ margin: 0 }}>{v}</dd></div>)}
          </dl>
        </section>
      </div>
    </div>
  );
}
