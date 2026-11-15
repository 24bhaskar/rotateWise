import { BookOpen, ChevronDown, Sprout } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useStateData } from "../lib/data";
import { useAppParams, withQuery } from "../lib/url";
import { CountyChooser } from "./CountyChooser";
import { Logo } from "./Logo";

export const STEPS = [
  { path: "/field", label: "Your county" },
  { path: "/risks", label: "What hurts yields" },
  { path: "/options", label: "Your options" },
  { path: "/next", label: "Talk it over" },
];

export function Layout() {
  const { data: state } = useStateData();
  const { fips, setCounty, query } = useAppParams();
  const loc = useLocation();
  const dialog = useRef<HTMLDialogElement>(null);
  const county = state?.counties.find((c) => c.fips === fips);
  const stepIdx = STEPS.findIndex((s) => loc.pathname.startsWith(s.path));
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);

  return (
    <>
      <a href="#main" className="sr-only">Skip to content</a>
      <header className="header">
        <div className="wrap header-row">
          <Link to={withQuery("/", query)} className="brand"><Logo /> RotateWise</Link>
          <span className="header-spacer" />
          {county && (
            <button type="button" className="county-pill" onClick={() => dialog.current?.showModal()} aria-haspopup="dialog">
              <Sprout size={16} aria-hidden="true" /> {county.name} County <ChevronDown size={16} aria-hidden="true" />
            </button>
          )}
          <NavLink to={withQuery("/evidence", query)} className="navlink"><BookOpen size={16} style={{ display: "inline", verticalAlign: -3 }} aria-hidden="true" /> Evidence</NavLink>
        </div>
        {stepIdx >= 0 && (
          <nav className="wrap" aria-label="Steps">
            <ol className="steps">
              {STEPS.map((s, i) => (
                <li key={s.path}>
                  <NavLink to={withQuery(s.path, query)} className={i < stepIdx ? "done" : undefined} aria-current={i === stepIdx ? "step" : undefined}>
                    <span className="dot">{i + 1}</span>{s.label}
                  </NavLink>
                </li>
              ))}
            </ol>
          </nav>
        )}
      </header>

      <dialog ref={dialog} className="card" style={{ maxWidth: 720, width: "92vw", border: "1px solid var(--line)", color: "var(--ink)" }}
              aria-label="Choose a county" onClick={(e) => e.target === dialog.current && dialog.current?.close()}>
        <h2 style={{ fontSize: "1.4rem" }}>Choose a county</h2>
        {state && <CountyChooser compact counties={state.counties} selected={fips}
                                 onSelect={(f) => { setCounty(f); dialog.current?.close(); }} />}
        <div className="btn-row" style={{ marginTop: 16 }}>
          <button type="button" className="btn btn-ghost" onClick={() => dialog.current?.close()}>Close</button>
        </div>
      </dialog>

      <main id="main"><Outlet /></main>

      <footer className="footer">
        <div className="wrap">
          <p><strong>RotateWise supports farmers and extension agents. It does not replace your judgment or local
            agricultural expertise.</strong> It describes county-scale conditions from past seasons (a hindcast), not a forecast.</p>
          <p className="small muted">Data: NASA POWER and MODIS, USDA NASS, NRCS, RMA, US Drought Monitor, NOAA SPC. A prototype built for
            NASA Space Apps and Veritas AI, November 2026. <Link to={withQuery("/evidence/data", query)}>Sources and methods</Link></p>
        </div>
      </footer>
    </>
  );
}
