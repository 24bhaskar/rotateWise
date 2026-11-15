import { useState } from "react";
import { signedPct } from "../lib/format";

/** Lightweight SVG bar chart of yearly yield vs trend (keeps the charting library off the guided pages). */
export function AnomalyBars({ data }: { data: { year: number; anom_pct: number }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 260, padL = 40, padB = 26, padT = 10;
  const max = Math.max(10, ...data.map((d) => Math.abs(d.anom_pct)));
  const lim = Math.ceil(max / 10) * 10;
  const y = (v: number) => padT + ((lim - v) / (2 * lim)) * (H - padT - padB);
  const bw = (W - padL) / data.length;
  const ticks = [-lim, -lim / 2, 0, lim / 2, lim];
  const h = hover === null ? null : data[hover];
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" style={{ width: "100%", height: "auto" }}
           aria-label={`Corn yield versus trend by year, ${data[0]?.year}-${data[data.length - 1]?.year}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={padL} x2={W} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--ink-3)" : "var(--line)"} />
            <text x={padL - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--ink-3)">{`${t}%`}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const top = y(Math.max(0, d.anom_pct)), bottom = y(Math.min(0, d.anom_pct));
          return (
            <g key={d.year} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <rect x={padL + i * bw} y={padT} width={bw} height={H - padT - padB} fill="transparent" />
              <rect x={padL + i * bw + bw * 0.15} y={top} width={bw * 0.7} height={Math.max(1, bottom - top)} rx={2}
                    fill={d.anom_pct < 0 ? "var(--rust)" : "var(--crop)"} opacity={hover === null || hover === i ? 1 : 0.45}>
                <title>{`${d.year}: ${signedPct(d.anom_pct)} vs trend`}</title>
              </rect>
              {(i % 4 === 0 || i === data.length - 1) && (
                <text x={padL + i * bw + bw / 2} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{d.year}</text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="small" style={{ minHeight: "1.6em", color: "var(--ink-2)" }} aria-live="polite">
        {h ? <><strong>{h.year}</strong>: corn yield {signedPct(h.anom_pct)} vs the county's trend</> : "Point at a bar to see the year."}
      </figcaption>
    </figure>
  );
}
