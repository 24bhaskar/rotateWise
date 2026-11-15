export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December"];

export const pct = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : `${v.toFixed(digits)}%`;
export const signedPct = (v: number | null | undefined, digits = 1) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const r = Number(Math.abs(v).toFixed(digits));
  return `${r === 0 ? "±" : v > 0 ? "+" : "−"}${r.toFixed(digits)}%`;
};

/** Plain names for what pulls yields DOWN. Every feature has a monotone constraint, so the direction is fixed. */
export const DRAG_PLAIN: Record<string, string> = {
  jul_tmax_mean: "Hot Julys (high average daytime temperature)",
  heat_days_jul_aug: "Many days above 30 °C in July and August",
  precip_jun_aug: "Low summer rainfall",
  precip_jul_aug: "Low July-August rainfall",
  water_balance_jja: "Summer water shortfall (less rain than the crop used)",
  gwetroot_aug_mean: "Dry soil in August",
  gwetroot_jul_mean: "Dry soil in July",
  tmin_aug_mean: "Warm August nights",
  spring_frost_days: "Late spring frosts",
  heavy_rain_days_mj: "Heavy May-June downpours",
  gdd_season: "Overall season warmth",
};
export const share = (v: number) => `${Math.round(v * 100)}%`;
export const num = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : v.toFixed(digits);

/** "1 in 3 years" style wording for a share of years. */
export function yearsWording(f: number) {
  if (f >= 0.95) return "almost every year";
  if (f <= 0.04) return "rarely";
  const n = Math.round(1 / f);
  return n <= 1 ? "most years" : `about 1 year in ${n}`;
}

export const CROP_LABEL: Record<string, string> = {
  corn: "Corn", soybean: "Soybean", oats: "Oats", red_clover: "Red clover",
  cereal_rye_before_soy: "Winter rye", cereal_rye_before_corn: "Winter rye", cereal_rye: "Cereal rye",
};
export const STRATEGY_COLOR: Record<string, string> = { A: "var(--c-a)", B: "var(--c-b)", C: "var(--c-c)" };
export const STRATEGY_SHORT: Record<string, string> = {
  A: "Keep corn → soybean", B: "Add winter rye", C: "Add oats with red clover",
};
