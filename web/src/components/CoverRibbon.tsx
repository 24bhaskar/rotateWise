import { CROP_LABEL, MONTHS, STRATEGY_SHORT } from "../lib/format";
import type { State, StrategyId } from "../lib/types";

/** Month-by-month soil cover for each rotation year (green = growing crop or cover, tan = bare soil). */
export function CoverRibbon({ cal, only }: { cal: State["strategy_calendar"]; only?: StrategyId[] }) {
  const ids = (only ?? (Object.keys(cal) as StrategyId[]));
  return (
    <div>
      <div className="ribbon-row" aria-hidden="true">
        <span />
        {MONTHS.map((m) => <span key={m} className="muted small" style={{ textAlign: "center" }}>{m[0]}</span>)}
      </div>
      {ids.map((k) => (
        <div key={k} style={{ marginBottom: "var(--s-3)" }}>
          <div className="small" style={{ fontWeight: 700, marginBottom: 4 }}>{STRATEGY_SHORT[k]}</div>
          {cal[k].years.map((y, i) => (
            <div key={i} className="ribbon-row" role="img"
                 aria-label={`${STRATEGY_SHORT[k]}, year ${i + 1} (${CROP_LABEL[y.grain]}): soil covered in ${y.cover.filter((c) => c > 0.5).length} of 12 months`}>
              <span className="muted small">Yr {i + 1} · {CROP_LABEL[y.grain]}</span>
              {y.cover.map((c, m) => (
                <span key={m} className="ribbon-cell" title={`${MONTHS[m]}: ${Math.round(c * 100)}% of the month covered`}
                      style={{ background: c > 0.02 ? `color-mix(in srgb, var(--crop) ${Math.round(25 + c * 75)}%, var(--soil-soft))` : "var(--soil-soft)",
                               outline: y.critical[m] > 0 ? "2px solid var(--wheat)" : undefined, outlineOffset: -2 }} />
              ))}
            </div>
          ))}
        </div>
      ))}
      <div className="legend small">
        <span className="ribbon-cell" style={{ width: 18, background: "var(--crop)" }} /> crop or cover growing
        <span className="ribbon-cell" style={{ width: 18, background: "var(--soil-soft)", marginLeft: 12 }} /> bare soil
        <span className="ribbon-cell" style={{ width: 18, outline: "2px solid var(--wheat)", outlineOffset: -2, marginLeft: 12 }} /> grain crop's sensitive weeks
      </div>
      <p className="chart-cap">Typical Iowa dates from USDA crop-progress reports (2000-2019); rye and clover follow cited extension guidance.
        Real dates vary by year and field.</p>
    </div>
  );
}
