"""B9.2 candidate models M0-M8 plus chain C1. Every model: fit(df) on training rows, predict(df).

`df` has the feature columns, `anom_pct` (target), `year`, `fips`, and `prev_anom` (persistence input).
Inner model selection (alpha, lambda, number of trees) always uses year-grouped folds of the training rows.
"""
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from pygam import LinearGAM, s
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from src.features import EXPECTED_SIGN, FEATURE_SETS

SEED = 42
ALPHAS = np.logspace(-2, 3, 20)
INNER_FOLDS = 4


def inner_folds(df):
    return GroupKFold(n_splits=INNER_FOLDS).split(df, groups=df.year)


def add_engineered(df):
    """M5 terms, defined before modelling: heat above 30 C and heat x dryness."""
    d = df.copy()
    d["hinge_tmax30"] = (d.jul_tmax_mean - 30).clip(lower=0)
    d["heat_x_dry"] = d.heat_days_jul_aug * (1 - d.gwetroot_aug_mean)
    return d


class Zero:
    name, family = "M0 zero anomaly (trend only)", "baseline"

    def fit(self, df):
        return self

    def predict(self, df):
        return np.zeros(len(df))


class Persistence:
    name, family = "M1 persistence", "baseline"

    def fit(self, df):
        return self

    def predict(self, df):
        return df.prev_anom.fillna(0).to_numpy()


class Linear:
    """Standardised ridge or elastic net; alpha chosen by inner year-grouped CV."""

    def __init__(self, feats, kind="ridge", l1_ratio=None, engineered=False, name=None):
        self.feats, self.kind, self.l1_ratio, self.engineered = feats, kind, l1_ratio, engineered
        self.name, self.family = name or f"{kind} {len(feats)}f", "linear"

    def _X(self, df):
        d = add_engineered(df) if self.engineered else df
        cols = self.feats + (["hinge_tmax30", "heat_x_dry"] if self.engineered else [])
        return d[cols].to_numpy(float), cols

    def _make(self, alpha):
        if self.kind == "ridge":
            return Ridge(alpha=alpha)
        return ElasticNet(alpha=alpha / 100, l1_ratio=self.l1_ratio, max_iter=20000)

    def fit(self, df):
        X, self.cols = self._X(df)
        y = df.anom_pct.to_numpy()
        scores = {}
        for a in ALPHAS:
            err = []
            for tr, va in inner_folds(df):
                sc = StandardScaler().fit(X[tr])
                m = self._make(a).fit(sc.transform(X[tr]), y[tr])
                err.append(np.mean((m.predict(sc.transform(X[va])) - y[va]) ** 2))
            scores[a] = np.mean(err)
        self.alpha = min(scores, key=scores.get)
        self.scaler = StandardScaler().fit(X)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = self._make(self.alpha).fit(self.scaler.transform(X), y)
        return self

    def predict(self, df):
        return self.model.predict(self.scaler.transform(self._X(df)[0]))

    def contributions(self, df):
        """Exact SHAP values for a linear model: coef * standardised deviation from the training mean."""
        z = self.scaler.transform(self._X(df)[0])
        return pd.DataFrame(z * self.model.coef_, columns=self.cols, index=df.index)


class GAM:
    name, family = "M6 GAM", "gam"

    def __init__(self, feats, n_splines=6, lams=(0.3, 3, 30)):
        self.feats, self.n_splines, self.lams = feats, n_splines, lams
        self.name = f"M6 GAM {len(feats)}f"

    def _gam(self, lam):
        cons = {1: "monotonic_inc", -1: "monotonic_dec", 0: None}
        terms = None
        for i, f in enumerate(self.feats):
            t = s(i, n_splines=self.n_splines, lam=lam, constraints=cons[EXPECTED_SIGN[f]])
            terms = t if terms is None else terms + t
        return LinearGAM(terms)

    def fit(self, df):
        X, y = df[self.feats].to_numpy(float), df.anom_pct.to_numpy()
        scores = {}
        for lam in self.lams:
            err = []
            for tr, va in inner_folds(df):
                g = self._gam(lam).fit(X[tr], y[tr])
                err.append(np.mean((g.predict(X[va]) - y[va]) ** 2))
            scores[lam] = np.mean(err)
        self.lam = min(scores, key=scores.get)
        self.model = self._gam(self.lam).fit(X, y)
        return self

    def predict(self, df):
        return self.model.predict(df[self.feats].to_numpy(float))


class LGBM:
    family = "tree"

    def __init__(self, feats, num_leaves=6, max_depth=3, min_child_samples=100, reg_lambda=10, cap=500,
                 objective="regression", alpha=None, name=None):
        self.feats = feats
        self.params = dict(num_leaves=num_leaves, max_depth=max_depth, min_child_samples=min_child_samples,
                           reg_lambda=reg_lambda, learning_rate=0.03, subsample=0.7, subsample_freq=1,
                           colsample_bytree=0.7, random_state=SEED, verbose=-1, objective=objective,
                           monotone_constraints=[EXPECTED_SIGN[f] for f in feats])
        if alpha is not None:
            self.params["alpha"] = alpha
        if objective == "quantile":  # LightGBM does not allow monotone constraints with the quantile loss
            self.params.pop("monotone_constraints")
        self.cap = cap
        self.name = name or f"M7 LGBM l{num_leaves} d{max_depth} m{min_child_samples} r{reg_lambda}"

    def fit(self, df):
        X, y = df[self.feats], df.anom_pct
        best = []
        for tr, va in inner_folds(df):  # early stopping on inner held-out years
            m = lgb.LGBMRegressor(n_estimators=self.cap, **self.params)
            m.fit(X.iloc[tr], y.iloc[tr], eval_set=[(X.iloc[va], y.iloc[va])],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
            best.append(m.best_iteration_ or self.cap)
        self.n_estimators = max(int(np.mean(best)), 10)
        self.model = lgb.LGBMRegressor(n_estimators=self.n_estimators, **self.params).fit(X, y)
        return self

    def predict(self, df):
        return self.model.predict(df[self.feats])


class RF:
    name, family = "M8 random forest (shallow)", "tree"

    def __init__(self, feats):
        self.feats = feats

    def fit(self, df):
        self.model = RandomForestRegressor(n_estimators=300, max_depth=4, min_samples_leaf=50, max_features=0.5,
                                           random_state=SEED, n_jobs=-1).fit(df[self.feats], df.anom_pct)
        return self

    def predict(self, df):
        return self.model.predict(df[self.feats])


class Average:
    family = "ensemble"

    def __init__(self, a, b, name):
        self.a, self.b, self.name = a, b, name

    def fit(self, df):
        self.a.fit(df)
        self.b.fit(df)
        return self

    def predict(self, df):
        return (self.a.predict(df) + self.b.predict(df)) / 2


class StateLocalChain:
    """C1: stage 1 predicts the statewide mean anomaly of a year from state-mean features (ridge, ~19 points);
    stage 2 predicts each county's deviation from the state mean from its feature deviations."""
    name, family = "C1 state + local chain", "chain"

    def __init__(self, feats):
        self.feats = feats

    def _split(self, df):
        state = df.groupby("year")[self.feats].transform("mean")
        return state, df[self.feats] - state

    def fit(self, df):
        state, dev = self._split(df)
        ys = df.groupby("year").anom_pct.transform("mean")
        sdf = state.assign(anom_pct=ys, year=df.year, fips=df.fips).groupby("year").first().reset_index()
        self.s1 = Linear(self.feats).fit(sdf)  # one row per year, so inner folds are year folds
        ddf = dev.assign(anom_pct=df.anom_pct - ys, year=df.year)
        self.s2 = Linear(self.feats).fit(ddf)
        return self

    def predict(self, df):
        state, dev = self._split(df)
        return self.s1.predict(state) + self.s2.predict(dev.assign(year=df.year))


def candidates(crop):
    """The pre-declared ladder (<= ~20 configs across M3-M8). Same list for both crops."""
    S0, S1, S2 = FEATURE_SETS["S0"], FEATURE_SETS["S1"], FEATURE_SETS["S2"]
    c = {
        "M0": Zero(), "M1": Persistence(),
        "M2": Linear(S0, name="M2 ridge S0 (3 features)"),
        "M3_S1": Linear(S1, name="M3 ridge S1"), "M3_S2": Linear(S2, name="M3 ridge S2"),
        "M4_l0.2": Linear(S2, "enet", 0.2, name="M4 elastic net S2 l1=0.2"),
        "M4_l0.5": Linear(S2, "enet", 0.5, name="M4 elastic net S2 l1=0.5"),
        "M4_l0.8": Linear(S2, "enet", 0.8, name="M4 elastic net S2 l1=0.8"),
        "M5": Linear(S1, engineered=True, name="M5 ridge S1 + hinge/interaction"),
        "M6_S0": GAM(S0), "M6_S1": GAM(S1),
        "M8": RF(S2),
    }
    rng = np.random.default_rng(SEED)
    grid = [(l, d, m, r) for l in (4, 6, 8) for d in (2, 3, 4) for m in (50, 100, 200) for r in (1, 10, 50)]
    for i in rng.choice(len(grid), size=9, replace=False):
        l, d, m, r = grid[i]
        c[f"M7_l{l}d{d}m{m}r{r}"] = LGBM(S2, l, d, m, r)
    return c
