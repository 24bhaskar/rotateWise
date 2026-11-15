import { Droplets, Sprout, Tractor, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { SLIDER_KEYS } from "../lib/scoring";
import type { SliderKey, Sliders } from "../lib/types";

const META: Record<SliderKey, { label: string; icon: ReactNode; hint: string }> = {
  water: { label: "Conserve water", icon: <Droplets size={18} />, hint: "Keep crops' sensitive weeks out of the hot, dry months" },
  soil: { label: "Soil health", icon: <Sprout size={18} />, hint: "Keep soil covered when storms come" },
  income: { label: "Income", icon: <Wallet size={18} />, hint: "Steady returns per acre" },
  labor: { label: "Low labour", icon: <Tractor size={18} />, hint: "Fewer extra field passes and equipment" },
};

/** Four 0-5 importance pickers. */
export function PriorityPicker({ value, onChange }: { value: Sliders; onChange: (k: SliderKey, v: number) => void }) {
  return (
    <div className="prio">
      {SLIDER_KEYS.map((k) => (
        <fieldset key={k} className="prio-item" style={{ margin: 0 }}>
          <legend className="sr-only">{META[k].label}</legend>
          <div className="prio-head"><span style={{ color: "var(--crop)" }} aria-hidden="true">{META[k].icon}</span>{META[k].label}</div>
          <p className="small muted" style={{ marginBottom: 8 }}>{META[k].hint}</p>
          <div className="dots" role="group" aria-label={`${META[k].label} importance`}>
            {[0, 1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" aria-pressed={value[k] === n} aria-label={`${n} of 5`} onClick={() => onChange(k, n)}>{n}</button>
            ))}
          </div>
          <div className="dots-scale"><span>Not important</span><span>Very important</span></div>
        </fieldset>
      ))}
    </div>
  );
}
