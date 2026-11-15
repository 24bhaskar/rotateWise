// Mirror of src/rotations.py criterion_weights / score / rank / weight_sensitivity.
// Python computes every criterion value; the browser only re-weights them with the visitor's priorities.
import type { Criterion, CriteriaByStrategy, SliderKey, Sliders, StrategyId } from "./types";

export const CRITERIA: Criterion[] = ["StressExposure", "BareAndErosion", "WaterUse", "SoilHealth", "IncomeStability", "LaborBurden"];
export const SLIDER_KEYS: SliderKey[] = ["water", "soil", "income", "labor"];
export const SLIDERS: Record<SliderKey, Partial<Record<Criterion, number>>> = {
  water: { WaterUse: 0.5, StressExposure: 0.5 },
  soil: { SoilHealth: 0.5, BareAndErosion: 0.5 },
  income: { IncomeStability: 1.0 },
  labor: { LaborBurden: 1.0 },
};

export function criterionWeights(sliders: Sliders, excluded: Partial<Record<Criterion, string>>) {
  let s: Sliders = { ...sliders };
  for (const k of SLIDER_KEYS) s[k] = Math.max(Number(s[k]) || 0, 0);
  let note: string | null = null;
  if (SLIDER_KEYS.every((k) => s[k] === 0)) {
    s = { water: 1, soil: 1, income: 1, labor: 1 };
    note = "All priorities were zero, so equal weights are used.";
  }
  const lam = Object.fromEntries(CRITERIA.map((c) => [c, 0])) as Record<Criterion, number>;
  for (const k of SLIDER_KEYS) {
    // an excluded criterion's share moves to the slider's remaining criteria, so each priority keeps its weight
    const kept = Object.entries(SLIDERS[k]).filter(([c]) => !(c in excluded)) as [Criterion, number][];
    const total = kept.reduce((a, [, v]) => a + v, 0);
    for (const [c, share] of kept) lam[c] += (s[k] * share) / total;
  }
  const tot = CRITERIA.reduce((a, c) => a + lam[c], 0);
  for (const c of CRITERIA) lam[c] /= tot;
  return { weights: lam, note };
}

export function score(crit: CriteriaByStrategy, weights: Record<Criterion, number>): Record<StrategyId, number> {
  const out = {} as Record<StrategyId, number>;
  for (const k of Object.keys(crit) as StrategyId[]) {
    out[k] = CRITERIA.reduce((a, c) => a + weights[c] * (crit[k][c] ?? 0), 0);
  }
  return out;
}

/** Highest score first; ties keep the A, B, C order (same as Python's stable sort). */
export function rank(scores: Record<StrategyId, number>): StrategyId[] {
  return (Object.keys(scores) as StrategyId[]).sort((a, b) => scores[b] - scores[a]);
}

// Small seeded PRNG + Gamma(1) draws, so the sensitivity panel is stable between renders.
function mulberry32(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Dirichlet(1,1,1,1) priority mixes: share of draws where each strategy ranks first, and its rank range. */
export function weightSensitivity(crit: CriteriaByStrategy, excluded: Partial<Record<Criterion, string>>, n = 2000, seed = 42) {
  const rnd = mulberry32(seed);
  const ids = Object.keys(crit) as StrategyId[];
  const firsts = Object.fromEntries(ids.map((k) => [k, 0])) as Record<StrategyId, number>;
  const ranks = Object.fromEntries(ids.map((k) => [k, [] as number[]])) as Record<StrategyId, number[]>;
  for (let i = 0; i < n; i++) {
    const g = SLIDER_KEYS.map(() => -Math.log(1 - rnd())); // Gamma(1) = Exponential(1)
    const sum = g.reduce((a, b) => a + b, 0);
    const sl = Object.fromEntries(SLIDER_KEYS.map((k, j) => [k, g[j] / sum])) as Sliders;
    const order = rank(score(crit, criterionWeights(sl, excluded).weights));
    firsts[order[0]] += 1;
    order.forEach((k, j) => ranks[k].push(j + 1));
  }
  return Object.fromEntries(ids.map((k) => [k, {
    shareFirst: firsts[k] / n, rankMin: Math.min(...ranks[k]), rankMax: Math.max(...ranks[k]),
  }])) as Record<StrategyId, { shareFirst: number; rankMin: number; rankMax: number }>;
}
