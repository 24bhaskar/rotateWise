import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Term } from "../../components/Term";
import { ErrorNote, Loading } from "../../components/ui";
import { useEvidence } from "../../lib/data";
import { num, signedPct } from "../../lib/format";

export function Failures() {
  const { data: s, error } = useEvidence();
  if (error) return <ErrorNote message={error} />;
  if (!s) return <Loading />;
  const f = s.failures;
  const c12 = f.y2012.corn, c20 = f.y2020.corn, s20 = f.y2020.soy;

  const usdm = (y: number) => f.usdm.filter((u) => u.year === y).map((u) => ({ week: u.week.slice(5), severe: u.d2, extreme: u.d3 }));
  const ndvi = f.ndvi?.series ?? [];
  const augByYear = Object.entries(ndvi.reduce<Record<string, number[]>>((acc, p) => {
    if (p.date.slice(5, 7) === "08") (acc[p.date.slice(0, 4)] ??= []).push(p.value);
    return acc;
  }, {})).map(([y, v]) => ({ year: y, ndvi: v.reduce((a, b) => a + b, 0) / v.length }));
  const rma = ["Story County", "Iowa"].map((area) => {
    const rows = f.rma.filter((r) => r.area === area && r.crop === "corn");
    const get = (y: number, g: string) => rows.filter((r) => r.year === y && r.cause_group === g).reduce((a, r) => a + r.indemnity_musd, 0);
    return { area, rows: [2012, 2020].map((y) => ({ year: String(y), drought: get(y, "drought"), wind: get(y, "wind"), other: get(y, "hail") + get(y, "excess moisture") + get(y, "heat") + get(y, "other") })) };
  });

  return (
    <div className="stack">
      <section className="card">
        <p className="eyebrow">Where it works, partly</p>
        <h2 className="h3">The 2012 drought</h2>
        <p>We hid 2012 from the model and asked it to predict. Statewide, it said corn would fall <strong>{signedPct(c12.state_pred, 0)}</strong>;
          the real drop was <strong>{signedPct(c12.state_actual, 0)}</strong>. Right direction, about half the size: the model shrinks extreme years.
          In Story County it predicted {signedPct(c12.demo_pred, 0)} vs {signedPct(c12.demo_actual, 0)} actual.</p>
        <div className="grid grid-2">
          <div>
            <p className="small" style={{ fontWeight: 700 }}>US Drought Monitor, Story County, 2012</p>
            <div className="chart" style={{ height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={usdm(2012)} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="week" tick={{ fill: "var(--ink-3)", fontSize: 11 }} interval={7} />
                  <YAxis tick={{ fill: "var(--ink-3)", fontSize: 11 }} domain={[0, 100]} unit="%" />
                  <Tooltip contentStyle={{ borderRadius: 10 }} />
                  <Legend />
                  <Line dataKey="severe" name="Severe drought or worse" stroke="var(--wheat)" strokeWidth={2} dot={false} />
                  <Line dataKey="extreme" name="Extreme or worse" stroke="var(--rust)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-cap">Share of the county's area, weekly. An independent check, not used by the model.</p>
          </div>
          <div>
            <p className="small" style={{ fontWeight: 700 }}>NASA MODIS crop greenness in August (<Term k="NDVI">NDVI</Term>), Story County</p>
            <div className="chart" style={{ height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={augByYear} margin={{ left: -16, right: 8 }}>
                  <XAxis dataKey="year" tick={{ fill: "var(--ink-3)", fontSize: 11 }} interval={3} />
                  <YAxis domain={[0.5, 0.9]} tick={{ fill: "var(--ink-3)", fontSize: 11 }} />
                  <Tooltip formatter={(v) => num(Number(v), 2)} contentStyle={{ borderRadius: 10 }} />
                  <Bar dataKey="ndvi" radius={[3, 3, 0, 0]} fill="var(--c-model)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-cap">Average of August 16-day composites, 3×3 km box at the county centre. Lower = stressed or damaged canopy.</p>
          </div>
        </div>
      </section>

      <section className="card">
        <p className="eyebrow">Where it fails</p>
        <h2 className="h3">The August 2020 derecho</h2>
        <p>On 10 August 2020 a derecho — a long line of violent windstorms — crossed Iowa. NOAA logged <strong>{f.spc.wind_reports_iowa} severe-wind
          reports</strong> in the state that day ({f.spc.story_county_reports} in Story County, up to {f.spc.max_speed_reported_mph_iowa} mph).
          Our model only sees temperature and rain, so it <strong>cannot see wind damage</strong>: for Story County corn it predicted
          {" "}{signedPct(c20.demo_pred, 0)} vs <strong>{signedPct(c20.demo_actual, 0)}</strong> actual. Soybeans, less damaged by wind, were predicted
          well statewide ({signedPct(s20.state_pred, 1)} vs {signedPct(s20.state_actual, 1)}).</p>
        <div className="grid grid-2">
          {rma.map((r) => (
            <div key={r.area}>
              <p className="small" style={{ fontWeight: 700 }}>Corn crop-insurance payouts by cause, {r.area} ($ millions)</p>
              <div className="chart" style={{ height: 220 }}>
                <ResponsiveContainer>
                  <BarChart data={r.rows} margin={{ left: -10, right: 8 }}>
                    <XAxis dataKey="year" tick={{ fill: "var(--ink-3)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "var(--ink-3)", fontSize: 11 }} />
                    <Tooltip formatter={(v) => `$${num(Number(v), 1)}M`} contentStyle={{ borderRadius: 10 }} />
                    <Legend />
                    <Bar dataKey="drought" name="Drought" fill="var(--wheat)" />
                    <Bar dataKey="wind" name="Wind" fill="var(--sky)" />
                    <Bar dataKey="other" name="Other" fill="var(--c-base)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>
        <p className="chart-cap">USDA Risk Management Agency cause-of-loss data: insurance claims, not measured yield loss.</p>
      </section>

      <section className="card">
        <h2 className="h3">Biggest misses in the test years (corn)</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>County</th><th className="num">Year</th><th className="num">Actual</th><th className="num">Predicted</th></tr></thead>
            <tbody>{f.largest_test_errors.corn.map((e, i) => (
              <tr key={i}><td>{e.county}</td><td className="num">{e.year}</td><td className="num">{signedPct(e.actual, 0)}</td><td className="num">{signedPct(e.predicted, 0)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
