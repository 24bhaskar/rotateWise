# Pre-committed model-selection rule

Written 2026-11-14, before any cross-validation result of the revised pipeline was produced
(the first row of `experiments/log.csv` is timestamped after this file).

Evidence unit: the held-out year. Development years 2000-2019, leave-one-year-out CV,
detrending refit inside every fold. Metrics are averaged over held-out years. Corn and soybean are selected separately.

1. A candidate must beat both M0 (zero anomaly) and M2 (3-feature ridge) in mean per-year RMSE,
   and have lower RMSE than M2 in a clear majority of years (at least 12 of 20).
2. Among candidates that qualify, choose the simplest model whose mean per-year RMSE is within one
   standard error (over years) of the best. Simplicity order: M2 < M3 < M4 < M5 < M6 < M8 < M7 < ensembles.
3. If the 90% year-bootstrap interval of the paired RMSE difference versus M2 includes zero, call it a tie
   and choose the simpler model.
4. Ensembles E1/E2 and chain C1 are tried only if their trigger in spec B9.3 holds
   (E1/E2: residual correlation between the best linear and best tree model below 0.8;
   C1: at least 60% of anomaly variance is shared statewide within a year, from `reports/eda.md`).
5. If nothing beats M2, M2 is the main model, and the write-up says so.

Hyperparameter budget: at most about 20 configurations across M3-M9 per crop, fixed seed 42, all logged.
