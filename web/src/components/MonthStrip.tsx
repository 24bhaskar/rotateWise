import { CloudRain, Droplets, Snowflake, Sun, Wind } from "lucide-react";
import type { ReactNode } from "react";
import { MONTHS, yearsWording } from "../lib/format";
import type { RiskMonth } from "../lib/types";

const ROWS: { key: keyof RiskMonth; label: string; icon: ReactNode; color: string; help: string }[] = [
  { key: "frost", label: "Frost", icon: <Snowflake size={15} />, color: "63,116,163", help: "at least one night at or below 0 °C" },
  { key: "heat", label: "Heat stress", icon: <Sun size={15} />, color: "168,72,42", help: "3 or more days above 30 °C" },
  { key: "dry_spell", label: "Dry spell", icon: <Wind size={15} />, color: "185,133,42", help: "10+ days in a row with almost no rain" },
  { key: "heavy_rain", label: "Heavy rain", icon: <CloudRain size={15} />, color: "61,122,74", help: "a day with more than 25 mm (1 inch) of rain" },
  { key: "deficit", label: "Water deficit", icon: <Droplets size={15} />, color: "107,79,58", help: "rain was less than the water the field used" },
];

/** 12-month risk calendar: colour strength = share of years (2000-2025) the month had that condition. */
export function MonthStrip({ risk }: { risk: RiskMonth[] }) {
  return (
    <div>
      <div className="months" role="table" aria-label="How often each risk occurs by month">
        <div role="row">
          <div role="columnheader"><span className="sr-only">Risk</span></div>
          {MONTHS.map((m) => <div key={m} className="head" role="columnheader">{m}</div>)}
        </div>
        {ROWS.map((row) => (
          <Row key={row.key} label={row.label} icon={row.icon}>
            {risk.map((r, i) => {
              const v = Number(r[row.key]) || 0;
              return (
                <div key={i} role="cell" className="cell" title={`${row.label} in ${MONTHS[i]}: ${yearsWording(v)} (${row.help})`}
                     style={{ background: `rgba(${row.color},${0.08 + v * 0.85})`, color: v > 0.55 ? "#fff" : "var(--ink-2)" }}>
                  {v >= 0.05 ? `${Math.round(v * 100)}` : ""}
                </div>
              );
            })}
          </Row>
        ))}
      </div>
      <p className="chart-cap">Numbers are the share of years (%), 2000-2025, in which that month had the condition. Hover a cell for details.
        Source: NASA POWER daily weather at the county centre.</p>
    </div>
  );
}

function Row({ label, icon, children }: { label: string; icon: ReactNode; children: ReactNode }) {
  return (
    <div role="row">
      <div className="rowlabel" role="rowheader">{icon}<span>{label}</span></div>
      {children}
    </div>
  );
}
