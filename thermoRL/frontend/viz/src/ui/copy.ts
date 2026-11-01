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
  fallbackFigures: [
    { file: "heatmaps_seed1.png", caption: "Heatmaps, seed 1 (labelled figure)" },
    { file: "timeseries_seed1.png", caption: "Time series, seed 1 (labelled figure)" },
    { file: "anim_packing_vs_thermal_predictive_seed1.gif", caption: "Packing vs thermal_predictive, seed 1 (labelled animation)" },
    { file: "anim_power_balance_vs_thermal_predictive_seed1.gif", caption: "Power_balance vs thermal_predictive, seed 1 (labelled animation)" },
  ],
} as const;
