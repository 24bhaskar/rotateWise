import { ArrowRight, CloudSun, ListChecks, Satellite, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { CountyChooser } from "../components/CountyChooser";
import { ErrorNote, Loading } from "../components/ui";
import { useStateData } from "../lib/data";
import { useAppParams, withQuery } from "../lib/url";

export function Home() {
  const { data: state, error } = useStateData();
  const { fips, setCounty, query } = useAppParams();
  if (error) return <ErrorNote message={error} />;
  if (!state) return <Loading />;
  const county = state.counties.find((c) => c.fips === fips);

  return (
    <div className="wrap">
      <section className="hero">
        <p className="eyebrow">For Iowa farmers and extension agents</p>
        <h1>Which crop rotation suits your county's weather?</h1>
        <p className="lede">RotateWise looks at 26 years of NASA weather records and USDA yields for your county, shows when
          your crops are most at risk, and compares three rotations against the things you care about.</p>
        <div className="how">
          <div className="how-item"><span className="icon"><Satellite size={22} /></span>
            <div><strong>Learns from past seasons</strong><p className="small muted">A model trained on 99 Iowa counties finds which summer
              weather cut corn and soybean yields.</p></div></div>
          <div className="how-item"><span className="icon"><CloudSun size={22} /></span>
            <div><strong>Maps your risky months</strong><p className="small muted">Frost, heat, dry spells and storms, month by month,
              for your county.</p></div></div>
          <div className="how-item"><span className="icon"><ListChecks size={22} /></span>
            <div><strong>Compares three options</strong><p className="small muted">Your current corn → soybean, adding winter rye, or
              adding oats with red clover.</p></div></div>
        </div>
      </section>

      <section className="card" aria-labelledby="pick">
        <h2 id="pick" style={{ fontSize: "1.5rem" }}>Start with your county</h2>
        <CountyChooser counties={state.counties} selected={fips} onSelect={setCounty} />
        <div className="btn-row" style={{ marginTop: "var(--s-5)" }}>
          <Link className="btn btn-primary" to={withQuery("/field", query)}>
            Continue with {county?.name} County <ArrowRight size={18} aria-hidden="true" />
          </Link>
          <span className="small muted">Takes about 5 minutes. Nothing you enter leaves your browser.</span>
        </div>
      </section>

      <section className="callout" style={{ margin: "var(--s-6) 0 var(--s-7)", display: "flex", gap: 12 }}>
        <ShieldCheck size={22} style={{ flex: "none", color: "var(--soil)" }} aria-hidden="true" />
        <p><strong>A conversation starter, not a prescription.</strong> RotateWise works at county scale and explains past seasons;
          it cannot see your field's soil, drainage, equipment or markets. Use it to prepare for a talk with your agronomist
          or county extension office.</p>
      </section>
    </div>
  );
}
