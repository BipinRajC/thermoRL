export const LEGEND_NOTE = "Scale fixed per experiment and seed; E11 and E12 scales differ";

export const COPY = {
  appTitle: "ThermoRL — closed-loop FMU replay",
  badge: "Replay of recorded runs · no live simulation",
  webglFallback: "WebGL is unavailable. Showing the labelled pre-rendered figures instead.",
  loading: "Loading replay data…",
  loadingFile: (file: string, done: number, total: number) => `Loading ${file} (${done}/${total})`,
  errorTitle: "Replay data could not be loaded",
  syncHint:
    "Run `npm run sync-replay` (exports must exist under thermoRL/backend/experiments/summit/<EID>/exports/replay_v1)",
  emptyNoExperiments: "No experiments are listed in index.json.",
  cPrimeVerified: "C′ verified (6 h repeat)",
  cPrimeNot: "not directly repeated",
  overlays: { tc: "Coolant °C", kw: "Rack kW", occupied: "Occupied" },
  drawers: { outcome: "Outcome", why: "Why?", about: "About this data" },
  labels: { experiment: "Experiment", seed: "Seed", comparison: "Comparison", overlay: "Overlay" },
  controls: {
    play: "Play",
    pause: "Pause",
    jumpToEval: "Jump to evaluation start",
    speed: "Speed",
    scrubber: "Time",
    speedOption: (s: number) => `${s} ticks/s`,
  },
  legend: {
    outOfRange: (n: number) => `${n} ${n === 1 ? "rack" : "racks"} outside scale this frame`,
  },
  timeline: {
    yAxis: "Max-rack modelled coolant °C",
    spreadAxis: "Spread (max − min) °C",
    before: "before evaluation window",
    label: "Timeline: max-rack modelled coolant °C and spread across the episode; click or drag to seek",
  },
  rack: {
    coolant: "Modelled coolant °C",
    power: "Rack power kW",
    shadeNote: "Grey: before evaluation window",
    label: (title: string) => `${title}: modelled coolant and rack power across the episode`,
  },
  outcome: {
    footer: "The preregistered rule decides; this viewer is descriptive.",
    gapCaption: "Per-seed gaps from the recorded decision (°C, time-mean max-rack modelled coolant)",
    gapSeed: "Seed",
    gapPower: "power_balance − thermal_predictive (°C)",
    gapPacking: "packing − thermal_predictive (°C)",
    metricsCaption: "Time-mean max-rack modelled coolant °C, evaluation window, per recorded run",
    metricsPolicy: "Policy",
    metricsSeed: (seed: number) => `seed ${seed}`,
    missing: "—",
  },
  about: {
    heading: { s2: "Decision timing (S2)", interval: "Interval semantics", pulse: "Pulse rings", precision: "Logged precision", repro: "Reproducibility", caveats: "Caveats" },
    recorded: "This viewer replays recorded runs; there is no new simulation.",
    bullets: [
      "Warm-up is capped (7200 s), not settled",
      "G1 thermal predictor parameters are a frozen heuristic",
      "Temperatures are modelled by the POWER9 cooling FMU, not measured on hardware",
      "45 °C is a reference value only",
    ],
    resultsLabel: "Full results write-up (docs/results/2026-11-parasparam-demo-results.md)",
    resultsUrl:
      "https://github.com/BipinRajC/thermoRL/blob/feat/parasparam-demo/docs/results/2026-11-parasparam-demo-results.md",
  },
  fallbackFigures: [
    { file: "heatmaps_seed1.png", caption: "Heatmaps, seed 1 (labelled figure)" },
    { file: "timeseries_seed1.png", caption: "Time series, seed 1 (labelled figure)" },
    { file: "anim_packing_vs_thermal_predictive_seed1.gif", caption: "Packing vs thermal_predictive, seed 1 (labelled animation)" },
    { file: "anim_power_balance_vs_thermal_predictive_seed1.gif", caption: "Power_balance vs thermal_predictive, seed 1 (labelled animation)" },
  ],
} as const;
