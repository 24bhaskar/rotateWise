// County, priorities and what-if settings live in the URL so any view can be shared or bookmarked.
import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { SLIDER_KEYS } from "./scoring";
import type { Sliders } from "./types";

export const DEMO_FIPS = "19169";
const DEFAULT_W = [3, 3, 3, 3];
let pendingW: string | null = null;

function parseWeights(w: string | null) {
  const raw = (w ?? "").split(",");
  return SLIDER_KEYS.map((_, i) => {
    const v = raw[i] === undefined || raw[i].trim() === "" ? NaN : Number(raw[i]);
    return Number.isInteger(v) && v >= 0 && v <= 5 ? v : DEFAULT_W[i];
  });
}

export function useAppParams() {
  const [params, setParams] = useSearchParams();
  const fips = params.get("county") ?? DEMO_FIPS;
  const weights = parseWeights(params.get("w"));
  const sliders = Object.fromEntries(SLIDER_KEYS.map((k, i) => [k, weights[i]])) as Sliders;
  const temp = Number(params.get("t") ?? 0);
  const rain = Number(params.get("r") ?? 0);

  const update = useCallback((patch: Record<string, string | null>) => {
    setParams((p) => {
      const n = new URLSearchParams(p);
      for (const [k, v] of Object.entries(patch)) (v === null ? n.delete(k) : n.set(k, v));
      return n;
    }, { replace: true });
  }, [setParams]);

  return {
    fips, sliders, temp: Number.isFinite(temp) ? temp : 0, rain: Number.isFinite(rain) ? rain : 0,
    setCounty: (f: string) => update({ county: f }),
    // React Router does not queue updates made before navigation commits, so quick successive clicks would
    // overwrite each other; build on the last value we set until the URL catches up.
    setSlider: (k: keyof Sliders, v: number) => {
      const cur = parseWeights(pendingW ?? params.get("w"));
      pendingW = SLIDER_KEYS.map((s, i) => (s === k ? v : cur[i])).join(",");
      const next = pendingW;
      setParams((p) => { const n = new URLSearchParams(p); n.set("w", next); return n; }, { replace: true });
      queueMicrotask(() => { if (pendingW === next) setTimeout(() => { if (pendingW === next) pendingW = null; }, 0); });
    },
    setWhatIf: (t: number, r: number) => update({ t: String(t), r: String(r) }),
    query: params.toString(),
  };
}

/** Build a link that keeps the current county/priorities. */
export const withQuery = (path: string, query: string) => (query ? `${path}?${query}` : path);
