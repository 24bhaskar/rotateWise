"""Per-row feature contributions (SHAP) for any final model, and the month-weight stress profile (B11.3)."""
import numpy as np
import pandas as pd

from src.features import FEATURE_MONTHS
from src.models import GAM, LGBM, RF, Average, Linear, StateLocalChain

MONTHS = list(range(4, 11))


def contributions(model, df):
    """Additive contributions per feature (rows x features). Exact for linear and tree models."""
    if isinstance(model, Linear):
        c = model.contributions(df)
        if model.engineered:  # fold engineered terms back onto their source features
            c["jul_tmax_mean"] += c.pop("hinge_tmax30")
            hx = c.pop("heat_x_dry")
            c["heat_days_jul_aug"] += hx / 2
            c["gwetroot_aug_mean"] += hx / 2
        return c
    if isinstance(model, (LGBM, RF)):
        import shap
        vals = shap.TreeExplainer(model.model).shap_values(df[model.feats])
        return pd.DataFrame(vals, columns=model.feats, index=df.index)
    if isinstance(model, GAM):
        X = df[model.feats].to_numpy(float)
        cols = {f: model.model.partial_dependence(term=i, X=X) for i, f in enumerate(model.feats)}
        c = pd.DataFrame(cols, index=df.index)
        return c - c.mean()
    if isinstance(model, Average):
        a, b = contributions(model.a, df), contributions(model.b, df)
        return (a.add(b, fill_value=0)) / 2
    if isinstance(model, StateLocalChain):
        state, dev = model._split(df)
        s1 = model.s1.contributions(state)
        s2 = model.s2.contributions(dev.assign(year=df.year))
        return s1.add(s2, fill_value=0)
    raise TypeError(type(model))


def month_weights(contrib):
    """Mean |contribution| per feature, spread evenly over its months, normalised over Apr-Oct."""
    imp = contrib.abs().mean()
    w = {m: 0.0 for m in MONTHS}
    for feat, v in imp.items():
        months = [m for m in FEATURE_MONTHS.get(feat, []) if m in w]
        for m in months:
            w[m] += v / len(months)
    tot = sum(w.values()) or 1.0
    return {m: round(v / tot, 4) for m, v in w.items()}
