import { AlertTriangle, BarChart3, ChevronDown, CircleHelp, HandHeart, Lightbulb, ThumbsUp } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { CROP_LABEL, MONTHS_LONG, STRATEGY_COLOR, STRATEGY_SHORT, share, signedPct } from "../lib/format";
import type { Card, Criterion, RawMetrics, State, StrategyId } from "../lib/types";
import { useAppParams, withQuery } from "../lib/url";

export const CRITERION_PLAIN: Record<Criterion, string> = {
  StressExposure: "Crops' sensitive weeks away from risky months",
  BareAndErosion: "Soil covered in storm season",
  IncomeStability: "Income steadiness",
  LaborBurden: "Little extra work",
  WaterUse: "Water use",
  SoilHealth: "Soil health",
};

function Section({ icon, title, children, open }: { icon: ReactNode; title: string; children: ReactNode; open?: boolean }) {
  return (
    <details open={open}>
      <summary><span aria-hidden="true" style={{ color: "var(--crop)" }}>{icon}</span>{title}<ChevronDown className="chev" size={18} aria-hidden="true" /></summary>
      <div className="detail-body">{children}</div>
    </details>
  );
}

export function StrategyCard({ card, rank, score, state, scenario, top, raw }: {
  card: Card; rank: number; score: number; state: State; top: boolean;
  scenario: { corn: number; soybean: number } | null; raw: Record<StrategyId, RawMetrics>;
}) {
  const { query } = useAppParams();
  const id = card.strategy_id as StrategyId;
  const cycle = state.strategy_calendar[id].years;
  const tc = card.trait_coverage;
  const estimated = state.calendar.some((r) => r.verified === "N" && cycle.some((y) => y.extras.includes(r.crop)));
  const headline = (() => {
    if (id === "A") return "Your current rotation: the baseline every other option is compared with.";
    if (id === "B") return `Keeps the soil covered over winter and spring: bare soil drops from ${share(raw.A.bare_fraction)} to ${share(raw.B.bare_fraction)} of the year.`;
    const oatsEnd = state.calendar.find((r) => r.crop === "oats" && r.event === "critical")?.end_month_day;
    const [mm, dd] = (oatsEnd ?? "07-09").split("-").map(Number);
    return `One year in three grows oats, whose sensitive weeks end around ${MONTHS_LONG[mm - 1]} ${dd} — before the riskiest heat.`;
  })();

  return (
    <article className={`strategy ${top ? "top" : ""}`} aria-labelledby={`s-${id}`}>
      <div className="strategy-head">
        <div className="strategy-title">
          <span className="rank" style={{ background: STRATEGY_COLOR[id] }} aria-label={`Rank ${rank}`}>{rank}</span>
          <div>
            <h3 id={`s-${id}`} style={{ margin: 0 }}>{STRATEGY_SHORT[id]}</h3>
            <div className="cycle" aria-label="Rotation cycle">
              {cycle.map((y, i) => (
                <span key={i} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  {i > 0 && <span aria-hidden="true">→</span>}
                  <span className="crop-chip">{CROP_LABEL[y.grain]}{y.extras.length ? ` + ${y.extras.map((e) => CROP_LABEL[e]).join(", ").toLowerCase()}` : ""}</span>
                </span>
              ))}
            </div>
          </div>
          {top && <span className="badge crop" style={{ marginLeft: "auto" }}>Best fit for your priorities</span>}
        </div>
        <div>
          <div className="small" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Fit with your priorities</span><span className="num">{Math.round(score * 100)} / 100</span>
          </div>
          <div className="scorebar" role="img" aria-label={`Fit score ${Math.round(score * 100)} out of 100`}>
            <div style={{ width: `${Math.max(3, score * 100)}%`, background: STRATEGY_COLOR[id] }} />
          </div>
        </div>
        <p style={{ margin: 0, fontSize: "1.05rem" }}>{headline}</p>
        <div className="badges">
          <span className="badge">{card.modeled_years} of {card.cycle_years} years modelled</span>
          <span className="badge">{tc.sourced} of {tc.total} crop facts sourced</span>
          {tc.unverified > 0 && <span className="badge wheat">Not yet checked by an expert</span>}
          {estimated && <span className="badge wheat">Some timing estimated</span>}
        </div>
      </div>

      <Section icon={<Lightbulb size={18} />} title="Why it was suggested"><p>{card.why_suggested}</p></Section>
      <Section icon={<BarChart3 size={18} />} title="What the numbers say">
        <ul>
          {card.evidence.map((e, i) => (
            <li key={i}>{e.claim}: <strong className="num">{typeof e.value === "number" ? `${Math.round(e.value * 100)}%` : e.value}</strong>{" "}
              <span className="small muted">(<Link to={withQuery("/evidence/data", query)}>{e.data_source_id.replace(/;/g, ", ")}</Link>)</span></li>
          ))}
          {scenario && card.modeled_years > 0 && (
            <li>With your what-if settings, the modelled corn / soybean years would average <strong>{signedPct(scenario.corn)}</strong> /{" "}
              <strong>{signedPct(scenario.soybean)}</strong> vs trend.</li>
          )}
        </ul>
        <div style={{ marginTop: 12 }}>
          {(Object.entries(card.criteria) as [Criterion, number | null][]).filter(([, v]) => v !== null).map(([k, v]) => (
            <div key={k} className="small" style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 8, alignItems: "center", marginBottom: 6 }}>
              <span>{CRITERION_PLAIN[k]}</span>
              <span className="scorebar" title={`${Math.round((v ?? 0) * 100)} of 100, compared with the other two options`}>
                <div style={{ width: `${Math.max(3, (v ?? 0) * 100)}%`, background: STRATEGY_COLOR[id] }} />
              </span>
            </div>
          ))}
          <p className="chart-cap">Bars compare the three options with each other (best of the three = full bar).</p>
        </div>
      </Section>
      <Section icon={<ThumbsUp size={18} />} title="Possible benefits"><ul>{card.benefits.map((b, i) => <li key={i}>{b}</li>)}</ul></Section>
      <Section icon={<CircleHelp size={18} />} title="What we don't know"><ul>{card.information_gaps.map((b, i) => <li key={i}>{b}</li>)}</ul></Section>
      <Section icon={<AlertTriangle size={18} />} title="Risks to review locally"><ul>{card.risks_needing_local_review.map((b, i) => <li key={i}>{b}</li>)}</ul></Section>
      <div className="support"><HandHeart size={18} aria-hidden="true" /> {card.support_line}</div>
    </article>
  );
}
