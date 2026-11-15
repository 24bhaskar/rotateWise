// Parity with Python: fixture written by src/export_web.py from src/rotations.py.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { CRITERIA, criterionWeights, rank, score, weightSensitivity } from "./scoring";
import type { CriteriaByStrategy, Criterion, Sliders, StrategyId } from "./types";

const fx = JSON.parse(readFileSync(new URL("../../public/data/fixtures/scoring.json", import.meta.url), "utf-8")) as {
  criteria: CriteriaByStrategy; excluded: Partial<Record<Criterion, string>>;
  cases: { sliders: Sliders; weights: Record<Criterion, number>; scores: Record<StrategyId, number>; rank: StrategyId[]; note: string | null }[];
  sensitivity: Record<StrategyId, { share_first: number; rank_min: number; rank_max: number }>;
};

describe("scoring parity with Python", () => {
  for (const c of fx.cases) {
    it(`sliders ${JSON.stringify(c.sliders)}`, () => {
      const { weights, note } = criterionWeights(c.sliders, fx.excluded);
      for (const k of CRITERIA) expect(weights[k]).toBeCloseTo(c.weights[k], 3);
      expect(CRITERIA.reduce((a, k) => a + weights[k], 0)).toBeCloseTo(1, 9);
      expect(note).toBe(c.note);
      const s = score(fx.criteria, weights);
      for (const k of Object.keys(c.scores) as StrategyId[]) expect(s[k]).toBeCloseTo(c.scores[k], 3);
      expect(rank(s)).toEqual(c.rank);
    });
  }

  it("excluded criteria never get weight", () => {
    const { weights } = criterionWeights({ water: 5, soil: 5, income: 0, labor: 0 }, fx.excluded);
    for (const k of Object.keys(fx.excluded) as Criterion[]) expect(weights[k]).toBe(0);
  });

  it("priority-mix sensitivity agrees with Python within sampling noise", () => {
    const js = weightSensitivity(fx.criteria, fx.excluded);
    for (const k of Object.keys(js) as StrategyId[]) {
      expect(Math.abs(js[k].shareFirst - fx.sensitivity[k].share_first)).toBeLessThan(0.04);
    }
  });
});
