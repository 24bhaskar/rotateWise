// Shapes of the JSON written by src/export_web.py.
export type StrategyId = "A" | "B" | "C";
export type SliderKey = "water" | "soil" | "income" | "labor";
export type Sliders = Record<SliderKey, number>;
export type Criterion = "StressExposure" | "BareAndErosion" | "WaterUse" | "SoilHealth" | "IncomeStability" | "LaborBurden";
export type CriteriaScores = Record<Criterion, number | null>;
export type CriteriaByStrategy = Record<StrategyId, CriteriaScores>;

export interface County { fips: string; name: string; lat: number; lon: number }

export interface Evidence { claim: string; data_source_id: string; metric: string; value: number | string }
export interface Card {
  strategy_id: StrategyId; name: string; criteria: CriteriaScores; excluded_criteria: string[];
  why_suggested: string; evidence: Evidence[]; benefits: string[]; information_gaps: string[];
  risks_needing_local_review: string[]; modeled_years: number; not_modeled_years: number; cycle_years: number;
  confidence_note: string; trait_coverage: { sourced: number; total: number; verified_by_human: number; unverified: number };
  sources: string[]; support_line: string;
}

export interface RawMetrics {
  stress_exposure: number; bare_fraction: number; erosion_exposure: number; labor_index: number;
  income_delta_usd_acre_yr: number; profit_variance_lower: boolean; crops: string[]; modeled_years: number; cycle_years: number;
}

export interface ScenarioCell { t: number; r: number; corn: number; soybean: number; clipped: number }
export interface Driver { feature: string; label: string; months: number[]; mean_negative_effect: number }
export interface RiskMonth { month: string; frost: number; heat: number; dry_spell: number; heavy_rain: number; deficit: number; r_m: number }

export interface CountyData {
  fips: string; name: string;
  glance: { jul_tmax_mean: number; heat_days_jul_aug: number; corn_2012: number | null; soy_2012: number | null;
            worst_corn_year: number | null; worst_corn_anom: number | null };
  anomalies: { corn: { year: number; anom_pct: number }[]; soybean: { year: number; anom_pct: number }[] };
  risk: RiskMonth[];
  drivers: { corn: Driver[]; soybean: Driver[] };
  scenario: ScenarioCell[];
  rotation: {
    raw: Record<StrategyId, RawMetrics>; criteria: CriteriaByStrategy; excluded: Partial<Record<Criterion, string>>;
    cards: Record<StrategyId, Card>;
    calendar_shifts: Record<string, { criteria: CriteriaByStrategy; stress_exposure: Record<StrategyId, number> }>;
    rye_passes: Record<string, CriteriaByStrategy>;
  };
}

export interface ModelSummary {
  mae: number; rmse: number; rmse_se: number; bias: number; spearman_within_year: number | null;
  skill_vs_m0?: number; boot: { mae: number[]; rmse: number[]; skill: number[]; diff_vs_ref?: number[] };
  conformal_90_test_coverage?: number; train_rmse?: number;
}
export interface CropMetrics {
  selected_model: string; selected_name: string;
  test_expanding_trend: Record<"M0" | "M1" | "M2" | "selected", ModelSummary> & {
    year_2025_only: Record<string, { rmse: number; state_actual: number; state_pred: number }> | null;
    year_2020: Record<string, { rmse: number; state_actual: number; state_pred: number }>;
  };
  test_fixed_trend: Record<"M0" | "M1" | "M2" | "selected", ModelSummary>;
  dev_cv: Record<string, ModelSummary>;
  train_vs_cv_gap: { train_rmse: number; cv_rmse: number };
  placebo: { shuffled_rmse_mean: number; runs: number[]; m0_rmse: number; real_rmse: number };
  spatial_block: { rmse: number; loyo_rmse: number };
  expanding_window_dev: { rmse: Record<string, number> };
  ablations: Record<string, number>;
  intervals: { conformal_90_halfwidth_pct: number; conformal_loyo_coverage_by_year_mean: number;
               conformal_worst_year_coverage: number; quantile_lgbm_90_coverage: number };
  selection_notes: { reason: string };
}

interface FullState {
  meta: { generated: string; demo_fips: string; temp_steps: number[]; rain_steps: number[]; dev_years: number[];
          test_years: number[]; support_line: string; months: string[]; power_cells: number };
  counties: County[];
  map_layers: Record<string, { mean_abs_corn_anom: number; heat_trend: number; wet_trend: number }>;
  stress: { corn: Record<string, number>; soybean: Record<string, number>; other_crops_timing_proxy: Record<string, number> };
  calendar: { crop: string; event: string; start_month_day: string; typical_month_day: string; end_month_day: string;
              source_id: string; rule: string; verified: string }[];
  strategy_calendar: Record<StrategyId, { name: string; years: { grain: string; extras: string[]; cover: number[]; critical: number[] }[] }>;
  strategies: Record<StrategyId, { name: string; cycle: string[] }>;
  sliders: Record<SliderKey, { label: string; criteria: Partial<Record<Criterion, number>> }>;
  criteria: Criterion[];
  traits: { crop: string; trait: string; value: string; scale: string; source_id: string; verified: string; notes: string }[];
  sources: { id: string; claim_supported: string; title: string; publisher: string; url: string; year: string;
             verified_by_human: string; status?: string; checked?: string }[];
  ssurgo: { drainage_class_pct_of_area: Record<string, number>; surface_organic_matter_pct_area_weighted: number;
            slope_class_pct_of_area: Record<string, number>; top_map_units: Record<string, number>; source: string; retrieved: string; note: string };
  evidence: {
    metrics: Record<"corn" | "soy", CropMetrics>;
    conformal: Record<"corn" | "soy", { halfwidth_pct: number }>;
    selection_rule: string; eda: string;
    experiments: { crop: string; model_id: string; cv_rmse: number; cv_mae: number; skill_vs_m0: number | null;
                   within_year_spearman: number | null; train_rmse: number; selected: boolean }[];
    diversity: Record<string, unknown>;
    by_year: Record<"corn" | "soy", { dev: { year: number; model_id: string; rmse: number; state_actual: number; state_pred: number }[];
                                      test: { year: number; model: string; rmse: number; state_actual: number; state_pred: number }[] }>;
    shap: Record<"corn" | "soy", { importance: { feature: string; label: string; months: number[]; mean_abs: number }[];
                                   dependence: Record<string, { x: number; effect: number }[]> }>;
  };
  failures: {
    y2012: Record<"corn" | "soy", { state_actual: number; state_pred: number; demo_actual: number; demo_pred: number }>;
    y2020: Record<"corn" | "soy", { state_actual: number; state_pred: number; demo_actual: number; demo_pred: number }>;
    largest_test_errors: Record<"corn" | "soy", { county: string; year: number; actual: number; predicted: number; error: number }[]>;
    spc: { wind_reports_iowa: number; story_county_reports: number; max_speed_reported_mph_iowa: number; page: string };
    rma: { year: number; crop: string; cause_group: string; area: string; indemnity_musd: number }[];
    usdm: { year: number; week: string; d0: number; d1: number; d2: number; d3: number; d4: number }[];
    ndvi?: { series: { date: string; value: number }[]; years: number[]; product: string };
  };
}

// state.json holds what the guided pages need; evidence.json the heavier material for the Evidence section.
type EvidenceKeys = "evidence" | "failures" | "sources" | "traits";
export type State = Omit<FullState, EvidenceKeys> & { conformal: Record<"corn" | "soy", { halfwidth_pct: number }> };
export type EvidenceData = Pick<FullState, EvidenceKeys>;
