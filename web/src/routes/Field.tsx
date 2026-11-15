import { Layers, Sun, Thermometer, TrendingDown } from "lucide-react";
import { AnomalyBars } from "../components/AnomalyBars";
import { IowaMap } from "../components/IowaMap";
import { Term } from "../components/Term";
import { ErrorNote, Loading, Pager, Stat, StepHeader } from "../components/ui";
import { useCounty, useStateData } from "../lib/data";
import { num, signedPct } from "../lib/format";
import { useAppParams } from "../lib/url";

const cToF = (c: number) => (c * 9) / 5 + 32;

export function Field() {
  const { fips, setCounty } = useAppParams();
  const { data: state, error: e1 } = useStateData();
  const { data: c, error: e2 } = useCounty(fips);
  if (e1 || e2) return <ErrorNote message={(e1 ?? e2)!} />;
  if (!state || !c) return <Loading />;
  const g = c.glance;
  const isDemo = fips === state.meta.demo_fips;
  const s = state.ssurgo;

  return (
    <div className="wrap page">
      <StepHeader step="Step 1 of 4" title={`${c.name} County at a glance`}
                  lede="Here is what 26 summers of NASA weather data and USDA yield reports say about your county." />

      <div className="grid grid-split">
        <div className="card">
          <IowaMap selected={fips} onSelect={setCounty} />
          <p className="chart-cap">Tap another county to switch. Each county is described by one NASA weather point at its centre
            (Iowa's 99 counties fall in only {state.meta.power_cells} NASA weather cells), so treat this as the conditions
            <em> around</em> your field, not on it.</p>
        </div>
        <div className="grid" style={{ alignContent: "start" }}>
          <Stat icon={<Thermometer size={20} />} tone="rust" value={`${num(g.jul_tmax_mean)} °C`}
                label={<>Average July high ({Math.round(cToF(g.jul_tmax_mean))} °F)</>} />
          <Stat icon={<Sun size={20} />} tone="wheat" value={Math.round(g.heat_days_jul_aug)}
                label={<><Term k="heat-stress days">Hot days</Term> above 30 °C (86 °F) in a typical July and August</>} />
          <Stat icon={<TrendingDown size={20} />} tone="soil" value={signedPct(g.corn_2012, 0)}
                label={<>Corn yield in the 2012 drought, compared with the county's usual <Term k="trend">trend</Term></>} />
        </div>
      </div>

      <section className="card" style={{ marginTop: "var(--s-5)" }}>
        <h2 style={{ fontSize: "1.4rem" }}>Good years and bad years for corn</h2>
        <p className="muted">Each bar is one season's corn yield above or below the county's long-run <Term k="trend">trend</Term>.
          Weather explains much of the swing; that is what the model learns from.</p>
        <AnomalyBars data={c.anomalies.corn} />
        {g.worst_corn_year && <p className="chart-cap">Worst season: {g.worst_corn_year} ({signedPct(g.worst_corn_anom, 0)}).
          Source: USDA NASS county yields.</p>}
      </section>

      {isDemo && (
        <section className="card" style={{ marginTop: "var(--s-5)" }}>
          <h2 style={{ fontSize: "1.4rem", display: "flex", gap: 8, alignItems: "center" }}><Layers size={22} aria-hidden="true" /> Soils in {c.name} County</h2>
          <div className="grid grid-3">
            <div><p className="eyebrow">Drainage</p>
              {Object.entries(s.drainage_class_pct_of_area).slice(0, 3).map(([k, v]) => <p key={k} style={{ margin: 0 }}>{k}: <strong>{Math.round(v)}%</strong></p>)}</div>
            <div><p className="eyebrow">Slope</p>
              {Object.entries(s.slope_class_pct_of_area).map(([k, v]) => <p key={k} style={{ margin: 0 }}>{k}: <strong>{Math.round(v)}%</strong></p>)}</div>
            <div><p className="eyebrow">Topsoil organic matter</p><p className="stat-value">{s.surface_organic_matter_pct_area_weighted}%</p>
              <p className="small muted">area-weighted average</p></div>
          </div>
          <p className="chart-cap">USDA-NRCS SSURGO soil survey, county-wide summary (retrieved {s.retrieved}). Your field's soil test is the better guide.</p>
        </section>
      )}

      <Pager back={{ to: "/", label: "Change county" }} next={{ to: "/risks", label: "What hurts yields here" }} />
    </div>
  );
}
