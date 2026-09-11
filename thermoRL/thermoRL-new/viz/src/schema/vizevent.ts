export type VizZone = {
  id: number;
  name: string;
  THI: number;
  T_c: number;
  load_kw: number;
  util: number;
  PUE: number;
  emergency: boolean;
  min_rack_thi: number;
  rack_spread: number;
};

export type VizEvent = {
  type: string;
  job_id: string | null;
  zone: number | null;
  rack: number | null;
  decision_id: string | null;
  defer_count: number | null;
};

export type VizMetrics = {
  jobs_completed: number;
  mean_wait_s: number;
  slo_compliance: number;
  violations_per_1k_jobs: number;
  hotspot_minutes_per_1k_jobs: number;
  emergency_events_per_1k_jobs: number;
  kg_co2_per_job: number;
  kwh_cooling_per_job: number;
  offered_demand_ratio: number;
  physical_facility_load_kw: number;
};

export type VizFrame = {
  t: number;
  sim_time_s: number;
  regime: string;
  policy_mode: string;
  zones: VizZone[];
  racks: Array<Array<{ THI: number; T_c: number; util: number; color?: string }>>;
  events: VizEvent[];
  metrics: VizMetrics;
  advanced: { lambdas?: number[] };
};

export type BundleMetrics = {
  thi_p10: number;
  thi_p90: number;
};
