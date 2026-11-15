import { geoMercator, geoPath } from "d3-geo";
import { useMemo } from "react";
import { useGeo } from "../lib/data";

type Props = {
  selected?: string;
  values?: Record<string, number>;
  colors?: [string, string, string];
  legend?: { low: string; high: string; title: string };
  onSelect?: (fips: string) => void;
  height?: number;
};

const W = 640, H = 420;

function mix(a: string, b: string, t: number) {
  // only used for hex colours resolved below
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`;
}

/** Iowa's 99 counties as an offline SVG (no map tiles). Click or Enter selects a county. */
export function IowaMap({ selected, values, colors = ["#f6e7c4", "#d9a441", "#8a4b1f"], legend, onSelect, height }: Props) {
  const { data: geo } = useGeo();
  const shapes = useMemo(() => {
    if (!geo) return [];
    const proj = geoMercator().fitSize([W, H], geo);
    const path = geoPath(proj);
    return geo.features.map((f) => ({ fips: String(f.properties?.fips), name: String(f.properties?.name), d: path(f) ?? "" }));
  }, [geo]);
  const [lo, hi] = useMemo(() => {
    const v = Object.values(values ?? {}).filter(Number.isFinite);
    return v.length ? [Math.min(...v), Math.max(...v)] : [0, 1];
  }, [values]);
  const fill = (fips: string) => {
    if (!values) return fips === selected ? "var(--crop)" : "var(--crop-soft)";
    const v = values[fips];
    if (!Number.isFinite(v)) return "var(--surface-2)";
    const t = hi > lo ? (v - lo) / (hi - lo) : 0.5;
    return t < 0.5 ? mix(colors[0], colors[1], t * 2) : mix(colors[1], colors[2], (t - 0.5) * 2);
  };
  if (!geo) return <div className="skeleton" style={height ? { height } : { aspectRatio: `${W} / ${H}`, minHeight: 0 }} aria-label="Loading map" />;
  const sel = shapes.find((s) => s.fips === selected);
  return (
    <div className="map">
      <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Map of Iowa counties" style={{ height, width: "100%" }}>
        {shapes.map((s) => (
          <path key={s.fips} d={s.d} fill={fill(s.fips)} className={s.fips === selected ? "selected" : undefined}
                tabIndex={onSelect ? 0 : -1} role={onSelect ? "button" : undefined}
                aria-label={`${s.name} County${values && Number.isFinite(values[s.fips]) ? `: ${values[s.fips].toFixed(1)}` : ""}`}
                onClick={() => onSelect?.(s.fips)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect?.(s.fips)}>
            <title>{`${s.name} County`}</title>
          </path>
        ))}
        {sel && <path d={sel.d} fill="none" stroke="var(--ink)" strokeWidth={2.6} pointerEvents="none" />}
      </svg>
      {values && legend && (
        <div className="legend">
          <span>{legend.low}</span>
          <span className="legend-bar" style={{ background: `linear-gradient(90deg, ${colors.join(",")})` }} />
          <span>{legend.high}</span>
          <span className="muted">· {legend.title}</span>
        </div>
      )}
    </div>
  );
}
