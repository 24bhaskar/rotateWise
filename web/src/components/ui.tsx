import { ArrowLeft, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAppParams, withQuery } from "../lib/url";

export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="wrap page" aria-busy="true"><div className="skeleton" aria-label={label} style={{ height: 320 }} /></div>;
}

export function ErrorNote({ message }: { message: string }) {
  return <div className="wrap page"><div className="callout alert"><p>Something went wrong loading the data: {message}</p></div></div>;
}

export function Stat({ icon, value, label, tone = "crop" }: { icon: ReactNode; value: ReactNode; label: ReactNode; tone?: string }) {
  return (
    <div className="card stat">
      <span className="stat-icon" style={{ background: `var(--${tone}-soft)`, color: `var(--${tone})` }} aria-hidden="true">{icon}</span>
      <span className="stat-value num">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export function Pager({ back, next }: { back?: { to: string; label: string }; next?: { to: string; label: string } }) {
  const { query } = useAppParams();
  return (
    <nav className="pager no-print" aria-label="Step navigation">
      {back ? <Link className="btn btn-ghost" to={withQuery(back.to, query)}><ArrowLeft size={18} aria-hidden="true" /> {back.label}</Link> : <span />}
      {next && <Link className="btn btn-primary" to={withQuery(next.to, query)}>{next.label} <ArrowRight size={18} aria-hidden="true" /></Link>}
    </nav>
  );
}

export function StepHeader({ step, title, lede }: { step?: string; title: ReactNode; lede?: ReactNode }) {
  return (
    <header style={{ marginBottom: "var(--s-6)" }}>
      {step && <p className="eyebrow">{step}</p>}
      <h1>{title}</h1>
      {lede && <p className="lede">{lede}</p>}
    </header>
  );
}
