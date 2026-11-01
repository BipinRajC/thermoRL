export const SCHEMA = "thermorl.replay.v1";

export type PolicyId =
  | "packing"
  | "node_balance"
  | "power_balance"
  | "coolest_rack"
  | "thermal_predictive";

export const TICK_COLUMNS = [
  "t_s",
  "it_kw_total",
  "n_running",
  "n_queued",
  "maxrack_c",
  "minrack_c",
  "argmax_rack",
  "pump_kw_sum",
] as const;
export type TickColumn = (typeof TICK_COLUMNS)[number];

export interface IndexEntry {
  id: string;
  short: string;
  label: string;
  catalog: string;
  default?: boolean;
}

export interface IndexFile {
  schema: string;
  experiments: IndexEntry[];
}

export interface ColourScale {
  min: number;
  max: number;
  scope: string;
}

export interface SeedEntry {
  seed: number;
  note: string;
  colour_scale_c: ColourScale;
  runs: Partial<Record<PolicyId, string>>;
}

export interface Comparison {
  id: string;
  left: PolicyId;
  right: PolicyId;
  default?: boolean;
}

export interface Catalog {
  schema: string;
  experiment: {
    id: string;
    short: string;
    workload_label: string;
    workload_note: string;
    system_label: string;
    scenario: string;
    fmu_sha256: string;
  };
  grid: {
    rows: number;
    cols: number;
    n_racks: number;
    nodes_per_rack: number;
    mapping: string;
    schematic_not_floor_plan: boolean;
  };
  time: {
    tick_s: number;
    n_ticks: number;
    first_t_s: number;
    last_t_s: number;
    eval_start_exclusive_s: number;
    eval_end_inclusive_s: number;
    pulse_window_s: number;
  };
  rack_kw_range: { idle_kw: number; peak_kw: number; basis: string };
  colormap: { name: string; lut: string[] };
  seeds: SeedEntry[];
  default_seed: number;
  comparisons: Comparison[];
  strings: {
    interval_semantics: string;
    s2: string;
    precision_note: string;
    pulse_rule: string;
  };
  unavailable_fields: string[];
  provenance: {
    export_source_sha: string;
    exporter: string;
    generated_utc: string;
    raw_inventory: string;
  };
}

export interface MetricsRow {
  name: string;
  policy: string;
  seed: number;
  maxrack_mean_c: number;
  [column: string]: string | number;
}

export interface FrozenOutcome {
  schema: string;
  experiment_id: string;
  headline: string;
  rule: string;
  decision: {
    decision: string;
    per_seed: Record<
      string,
      { packing_minus_thermal_c: number; power_minus_thermal_c: number }
    >;
    rule: string;
    value_beyond_power: boolean;
  };
  decision_sha256: string;
  metrics_sha256: string;
  metrics: MetricsRow[];
  experiment_statement: string;
  reproducibility_scope: string;
}

export interface FileEntry {
  path: string;
  dtype: "float32" | "float64" | "uint8" | "json" | "record";
  bytes: number;
  sha256: string;
  shape?: number[];
  columns?: string[];
  record_bytes?: number;
  rows_per_decision?: number;
  fields?: [string, string][];
  empty_rack?: number;
}

export interface RunMeta {
  schema: string;
  run_id: string;
  experiment_id: string;
  policy: PolicyId;
  seed: number;
  launch_sha: string;
  selected_attempt: number;
  c_prime_status: "verified_E12" | "inherited_not_remeasured";
  n_ticks: number;
  n_racks: number;
  n_decisions: number;
  n_events: number;
  source: {
    manifest_sha256: string;
    decisions_sha256: string;
    intervals_sha256: string;
    job_events_sha256: string;
  };
  metrics: MetricsRow;
  files: {
    rack_tc: FileEntry;
    rack_kw: FileEntry;
    rack_free: FileEntry;
    tick: FileEntry;
    events: FileEntry;
    decisions: FileEntry;
    candidates: FileEntry;
  };
}
