import { MapPin, Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { County } from "../lib/types";
import { IowaMap } from "./IowaMap";

/** Search box + clickable map. Used on the home page and in the header dialog. */
export function CountyChooser({ counties, selected, onSelect, compact }: {
  counties: County[]; selected: string; onSelect: (fips: string) => void; compact?: boolean;
}) {
  const [q, setQ] = useState("");
  const matches = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? counties.filter((c) => c.name.toLowerCase().startsWith(s)).slice(0, 8) : [];
  }, [q, counties]);
  return (
    <div className={compact ? "stack" : "grid grid-split"}>
      <div>
        <label className="field-label" htmlFor="county-search">Type your county</label>
        <div style={{ position: "relative" }}>
          <Search size={18} style={{ position: "absolute", left: 14, top: 15, color: "var(--ink-3)" }} aria-hidden="true" />
          <input id="county-search" className="search" style={{ paddingLeft: 40 }} placeholder="e.g. Story" value={q}
                 autoComplete="off" onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && matches[0] && onSelect(matches[0].fips)} />
        </div>
        {matches.length > 0 && (
          <ul role="listbox" aria-label="Matching counties" style={{ listStyle: "none", padding: 0, margin: "8px 0 0" }}>
            {matches.map((c) => (
              <li key={c.fips}>
                <button type="button" className="btn btn-ghost" style={{ width: "100%", justifyContent: "flex-start", marginBottom: 6 }}
                        onClick={() => onSelect(c.fips)}>
                  <MapPin size={16} aria-hidden="true" /> {c.name} County
                </button>
              </li>
            ))}
          </ul>
        )}
        <p className="small muted" style={{ marginTop: 12 }}>…or tap your county on the map. Story County is the worked example.</p>
      </div>
      <IowaMap selected={selected} onSelect={onSelect} height={compact ? 220 : undefined} />
    </div>
  );
}
