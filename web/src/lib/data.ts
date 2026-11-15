import { useEffect, useState } from "react";
import type { CountyData, EvidenceData, State } from "./types";

const cache = new Map<string, Promise<unknown>>();

function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(`/data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`Could not load ${path} (${r.status})`);
      return r.json();
    }));
  }
  return cache.get(path) as Promise<T>;
}

function useJson<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setData(null);
    load<T>(path).then((d) => live && setData(d)).catch((e) => live && setError(String(e.message ?? e)));
    return () => { live = false; };
  }, [path]);
  return { data, error };
}

export const useStateData = () => useJson<State>("state.json");
export const useCounty = (fips: string | null) => useJson<CountyData>(fips ? `county/${fips}.json` : null);
export const useEvidence = () => useJson<EvidenceData>("evidence.json");
export const useGeo = () => useJson<GeoJSON.FeatureCollection>("iowa.geo.json");
