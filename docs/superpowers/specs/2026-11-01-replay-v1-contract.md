# `thermorl.replay.v1` — Replay Data Contract (exporter ⇄ viewer)

**Status:** binding for both the backend exporter (Sonnet brief A5–A7) and the frontend viewer (`docs/superpowers/plans/2026-11-01-thermorl-replay-viewer.md`). **Date:** 2026-11-01. **Author:** Opus.

Where the brief's A5 sketch differs, **this document wins**: file names, the record layout, K, the colormap and the strings below.

**Purpose:** compact, hash-verified replay of **recorded** FMU runs.
- No values are recomputed or rescored in the browser.
- Headline numbers are copied verbatim from frozen results.

---

## 1. Layout

There is one tree per experiment `<EID>` ∈ {`E11_g4_synthetic`, `E12_g4_alibaba`}:

```
thermoRL/backend/experiments/summit/<EID>/exports/replay_v1/
  catalog.json
  frozen_outcome.json
  runs/<policy>_seed<s>/                  # policy ∈ {packing, power_balance, thermal_predictive}; s ∈ {1,2,3}
    run.json
    rack_tc.f32       rack_kw.f32       rack_free.u8      tick.f64
    events.json       decisions.json    candidates.bin
```

- The viewer receives a **synced copy** under `thermoRL/frontend/viz/public/replay/`:
  - `index.json`, written by the sync script;
  - `<EID>/…`, identical to the tree above.
- All binaries are **little-endian**, row-major, `[tick][rack]`.
- `tick` k ∈ 0…2159 ↔ `t_s = 10·(k+1)`; `rack` r ∈ 0…256.

---

## 2. `index.json` (written by the frontend sync script; not by the exporter)

```json
{ "schema": "thermorl.replay.v1",
  "experiments": [
    {"id": "E12_g4_alibaba",  "short": "E12", "label": "E12 — Alibaba-derived workload", "catalog": "E12_g4_alibaba/catalog.json", "default": true},
    {"id": "E11_g4_synthetic","short": "E11", "label": "E11 — Synthetic workload",       "catalog": "E11_g4_synthetic/catalog.json"} ] }
```

---

## 3. `catalog.json`

```json
{
  "schema": "thermorl.replay.v1",
  "experiment": {
    "id": "E12_g4_alibaba", "short": "E12",
    "workload_label": "Alibaba-derived",
    "workload_note": "Alibaba GPU 2023 (openb, default variant); small 1–2-node, low-density, bursty jobs",
    "system_label": "Summit POWER9 cooling FMU (modelled)",
    "scenario": "nominal (290 K)",
    "fmu_sha256": "0a6ca3777ed38b75a94ea8d293a68748077db5963fa4b897fdea515615d19233"
  },
  "grid": {"rows": 13, "cols": 20, "n_racks": 257, "nodes_per_rack": 18,
           "mapping": "row = r // 20, col = r % 20, origin lower-left", "schematic_not_floor_plan": true},
  "time": {"tick_s": 10, "n_ticks": 2160, "first_t_s": 10, "last_t_s": 21600,
           "eval_start_exclusive_s": 3600, "eval_end_inclusive_s": 21600, "pulse_window_s": 30},
  "rack_kw_range": {"idle_kw": 13.822619047619046, "peak_kw": 49.32325680272109,
                    "basis": "RAPS loss-inclusive rack power, from run manifests"},
  "colormap": {"name": "inferno", "lut": ["#000004", "...", "#fcffa4"]},
  "seeds": [
    {"seed": 1, "note": "seed 1 of 3",
     "colour_scale_c": {"min": 38.70223, "max": 42.413286, "scope": "all five policies of this seed"},
     "runs": {"packing": "runs/packing_seed1/run.json",
              "power_balance": "runs/power_balance_seed1/run.json",
              "thermal_predictive": "runs/thermal_predictive_seed1/run.json"}},
    {"seed": 2, "note": "seed 2 of 3", "colour_scale_c": {"…": "…"}, "runs": {"…": "…"}},
    {"seed": 3, "note": "seed 3 of 3 — ≈ seed 2 shifted 33 s; about two independent workload conditions in E12", "colour_scale_c": {"…": "…"}, "runs": {"…": "…"}}
  ],
  "default_seed": 1,
  "comparisons": [
    {"id": "pb_vs_tp", "left": "power_balance", "right": "thermal_predictive", "default": true},
    {"id": "packing_vs_tp", "left": "packing", "right": "thermal_predictive"}
  ],
  "strings": {
    "interval_semantics": "Rack power, free nodes and job counts are RAPS inputs at t − 10 s, held over the 10 s interval ending at t; coolant temperature is the FMU output at the end of that interval (t).",
    "s2": "<verbatim S2, §6>",
    "precision_note": "<verbatim, §6>",
    "pulse_rule": "Rings mark racks that received a job start in the 30 s ending at the displayed time (RAPS start time). A placement's power first appears in the rack power of the following 10 s interval. Rings are not a cooling effect."
  },
  "unavailable_fields": ["PUE", "carbon", "SLO", "emergency", "dual_prices", "THI_counterfactual", "regret", "energy_savings"],
  "provenance": {"export_source_sha": "<HEAD at export>", "exporter": "thermorl2/experiments/replay_export.py",
                 "generated_utc": "<iso>", "raw_inventory": "results/run_files.json"}
}
```

**Rules:**
- **E11** uses `workload_label: "Synthetic"` and `workload_note: "Generated synthetic workload; 1–32-node jobs, high power density"`. Its seed notes are plain "seed s of 3".
- **`colour_scale_c` for seed 1 must equal the recorded demo scales** within 1e-6: E11 39.252402–56.233641 °C, E12 38.702230–42.413286 °C. Otherwise the exporter **STOPS**.
  - Seeds 2 and 3 use the min/max of `t_c` over all five policies of that seed, across all 2160×257 samples.
- **`colormap.lut`** holds exactly 256 lowercase `#rrggbb` strings from matplotlib's `inferno` colormap (`matplotlib.colormaps['inferno'](i/255)` for i = 0…255). That is the same colormap as the labelled figures.

---

## 4. `frozen_outcome.json`

```json
{
  "schema": "thermorl.replay.v1",
  "experiment_id": "E12_g4_alibaba",
  "headline": "no material value on the homogeneous twin",
  "rule": "power_balance − thermal_predictive time-mean max-rack coolant over 3600 < t ≤ 21600 s must be ≥ 0.5 °C in every seed",
  "decision": { "…": "verbatim copy of results/decision.json" },
  "decision_sha256": "<sha256 of results/decision.json>",
  "metrics_sha256": "<sha256 of results/metrics.csv>",
  "metrics": [ {"name": "packing_seed1", "policy": "packing", "seed": 1, "maxrack_mean_c": 41.41086946629474, "…": "every numeric column of metrics.csv, parsed as numbers"} ],
  "experiment_statement": "<§6 per experiment>",
  "reproducibility_scope": "<verbatim, §6>"
}
```

- `metrics` holds all 15 rows (five policies × three seeds), in `metrics.csv` order. Non-numeric columns other than `name` and `policy` (for example `coolant_over_70_racks`) are omitted.

---

## 5. `run.json` and run files

```json
{
  "schema": "thermorl.replay.v1",
  "run_id": "E12_g4_alibaba:power_balance_seed1", "experiment_id": "E12_g4_alibaba",
  "policy": "power_balance", "seed": 1,
  "launch_sha": "<manifest.git.sha>", "selected_attempt": 1,
  "c_prime_status": "inherited_not_remeasured",
  "n_ticks": 2160, "n_racks": 257, "n_decisions": 21885, "n_events": "<count: starts = n_decisions; completes ≤ n_decisions (jobs running at the horizon have no complete)>",
  "source": {"manifest_sha256": "…", "decisions_sha256": "…", "intervals_sha256": "…", "job_events_sha256": "…"},
  "metrics": { "…": "this run's frozen_outcome.metrics row" },
  "files": {
    "rack_tc":   {"path": "rack_tc.f32",   "dtype": "float32", "shape": [2160, 257], "bytes": 2220480, "sha256": "…"},
    "rack_kw":   {"path": "rack_kw.f32",   "dtype": "float32", "shape": [2160, 257], "bytes": 2220480, "sha256": "…"},
    "rack_free": {"path": "rack_free.u8",  "dtype": "uint8",   "shape": [2160, 257], "bytes": 555120,  "sha256": "…"},
    "tick":      {"path": "tick.f64",      "dtype": "float64", "shape": [2160, 8],   "bytes": 138240,  "sha256": "…",
                  "columns": ["t_s", "it_kw_total", "n_running", "n_queued", "maxrack_c", "minrack_c", "argmax_rack", "pump_kw_sum"]},
    "events":    {"path": "events.json",   "dtype": "json", "bytes": 0, "sha256": "…"},
    "decisions": {"path": "decisions.json","dtype": "json", "bytes": 0, "sha256": "…"},
    "candidates":{"path": "candidates.bin","dtype": "record", "bytes": 0, "sha256": "…",
                  "record_bytes": 15, "rows_per_decision": 6,
                  "fields": [["rack", "uint16"], ["score", "float32"], ["t_c", "float32"], ["committed_kw", "float32"], ["free", "uint8"]],
                  "empty_rack": 65535}
  }
}
```

**Field rules:**
- **`c_prime_status`:** `"verified_E12"` only for E12 `thermal_predictive` seed 1. Every other run is `"inherited_not_remeasured"`.
- **`selected_attempt`:** from E12 `results/matrix_runtime.json`. E11 uses `1`.
- **`rack_tc`:** `t_c` from `intervals.parquet`, cast to float32.
- **`rack_kw`:** `kw`, cast to float32.
- **`rack_free`:** `free`, cast to uint8 (0–18).
- **`tick`** (float64), per tick:
  - `t_s`;
  - `it_kw_total`;
  - `n_running`;
  - `n_queued`;
  - `maxrack_c` = max over racks of float64 `t_c`;
  - `minrack_c` = min;
  - `argmax_rack` = lowest rack index attaining the max;
  - `pump_kw_sum` = Σ `pump_kw` over racks (modelled; **never displayed as savings**).
- **`events.json`** (columnar; `rack_offsets` has length `n_events + 1`, and the event's racks are `racks[rack_offsets[i]:rack_offsets[i+1]]`):

  ```json
  {"kind": [0, 1], "raps_t_s": [6, 1806], "job_id": [0, 0], "decision_index": [0, -1],
   "rack_offsets": [0, 1, 2], "racks": [0, 0]}
  ```

  - `kind`: 0 = start, 1 = complete.
  - `racks` = sorted unique `node // 18`.
  - Events are ordered by (`raps_t_s`, completes before starts, `decision_index`).
- **`decisions.json`** (columnar, in `decision_index` order, so `raps_t_s` is non-decreasing):

  ```json
  {"decision_index": [], "raps_t_s": [], "job_id": [], "nodes_required": [], "rule": [],
   "job_kw": [], "t_obs_s": [], "chosen_offsets": [], "chosen_racks": [],
   "n_ties_at_logged_best": [], "chosen_is_logged_best": []}
  ```

  - `rule` ∈ {`"single"`, `"span"`}.
  - `chosen_offsets` has length `n_decisions + 1`.
  - `n_ties_at_logged_best` = the number of racks whose logged score equals the maximum logged score.
  - `chosen_is_logged_best` is true when the first chosen rack has the maximum logged score.
- **`candidates.bin`:** for decision i, rows `[i·6, i·6+6)`, each 15 bytes (`<HfffB`).
  - Rows 0–4 are the **top 5 racks by logged score**, descending; ties go to the lower rack index (the placement rule).
  - Row 5 holds the first chosen rack if it is not already in rows 0–4. Otherwise the rack field is `65535` (empty).
  - Values are the **logged six-decimal** values, cast to float32.
  - **Size note:** 21,885 decisions × 6 × 15 B ≈ 1.97 MB.

---

## 6. Exact strings

| Key | Text |
|---|---|
| `s2` | published view = FMU endpoint t+Δ of interval driven by P(t); decisions in (t, t+Δ) observe it (≤9 s hold-power forecast, E10 max 10 s per-rack change 0.31 °C, p99 0.057 °C); no future-decision information; identical for all policies. |
| `precision_note` | Logged six-decimal context. Live decisions used full precision; near-ties below logging precision occur (thermal_predictive reproduces from logged context ≈ 94.8 % in E11 and ≈ 97.7 % in E12). This view shows logged values only; it does not reconstruct or rescore decisions. |
| `experiment_statement` (E11) | E11 (synthetic): no material value beyond power balancing (PB−TP +0.342, −0.147, −0.071 °C). Packing ≈ thermal_predictive on the primary metric (packing−TP +0.08, −0.11, +0.28 °C); no consistent primary ordering. |
| `experiment_statement` (E12) | In E12 (small, low-density, bursty Alibaba-derived jobs), thermal_predictive had the lowest and packing the highest time-mean max-rack coolant temperature in all three seeds (PB−TP 0.08–0.18 °C; packing−TP 0.35–0.44 °C). This is below the preregistered 0.5 °C materiality threshold, rests on about two independent workload conditions (seed 3 ≈ seed 2 shifted 33 s), and is descriptive only. |
| `reproducibility_scope` | Fresh-process reproducibility was verified for E10 packing seed 1 (2 h), for E11 seed-1 packing and power_balance over the first 2 h (exact prefix), and for E12 thermal_predictive seed 1 (6 h, byte-identical). No other configuration was directly repeated; no cross-machine portability is claimed. |

---

## 7. Size budget and checks (exporter side)

**Budget:**
- every file < 25 MB;
- each experiment's `replay_v1` ≤ 100 MB (9 runs at about 9–11 MB each).

If the budget is exceeded, STOP and report. Do not downsample time and do not reduce K below 5 without a new Bipin decision.

**Required exporter checks** (A6, against the verified raw copies), per run:
- `mean(tick.maxrack_c over 3600 < t_s ≤ 21600)` equals `metrics.csv` `maxrack_mean_c` within **1e-9**;
- `max |rack_tc − t_c| ≤ 5e-6 °C`;
- `it_kw_total` is identical across the three exported policies of a seed (1e-6 kW);
- decision count equals `manifest.decision_rows`;
- start events equal the decision count;
- every `files[*].sha256` matches the bytes;
- the seed-1 colour scale matches the recorded demo scale (1e-6);
- the source SHAs equal the manifest values.
