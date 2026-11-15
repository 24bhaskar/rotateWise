// Plain-language definitions, adapted from the app's Science tab.
export const GLOSSARY: Record<string, string> = {
  anomaly: "How far one year's yield fell above or below the county's long-run trend, in percent. Yields rise every year with better seed and machinery; the anomaly removes that rise so weather's effect shows.",
  trend: "The steady rise in a county's yields over time, fitted as a straight line using only earlier years.",
  evapotranspiration: "Water leaving the field: evaporation from the soil plus water the crop breathes out through its leaves (ET).",
  "water balance": "Rain minus evapotranspiration. Below zero means the crop is drawing down water stored in the soil.",
  "root-zone wetness": "How full the top metre of soil is with water, from 0 (dry) to 1 (saturated). NASA POWER takes it from a computer model (MERRA-2), not a direct measurement.",
  NDVI: "A satellite greenness index from 0 to about 0.9. Healthy summer corn is near 0.8-0.9; drought and wind damage lower it.",
  "heat-stress days": "Days when the high temperature goes above 30 °C (86 °F). Corn is most sensitive around silking in July.",
  "frost risk": "The share of years with at least one night at or below 0 °C (32 °F) in that month.",
  "cover crop": "A crop grown to protect and feed the soil between cash crops, such as cereal rye over winter.",
  "nitrogen fixation": "Legumes such as soybean and clover host bacteria that turn nitrogen from the air into plant food.",
  hindcast: "Explaining past seasons with the weather that actually happened. It is not a forecast of the coming season.",
  SHAP: "A way to split each prediction into how much each weather feature pushed it up or down.",
  "critical period": "The few weeks when a crop's yield is most sensitive to stress: silking for corn, pod fill for soybean, heading for oats.",
  reanalysis: "A weather record built by blending observations with a weather model, giving consistent daily values everywhere.",
  "prediction interval": "A range that should contain the real outcome 9 times out of 10, based on how wrong the model was in past years.",
};
