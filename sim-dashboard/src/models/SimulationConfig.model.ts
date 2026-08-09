import { addHours } from "date-fns";

export const workloadTypes = [
  "random", "benchmark", "peak", "idle", "synthetic", "multitenant", "replay", "randomAI",
] as const
export type WorkloadType = typeof workloadTypes[number]

const defaultPolices = ['replay', 'fcfs', 'priority', 'sjf', 'ljf']
export const schedulers = {
  default: {
    policies: [...defaultPolices],
  },
  multitenant: {
    policies: [...defaultPolices],
  },
  experimental: {
    policies: [
      ...defaultPolices, 'acct_fugaku_pts', 'acct_avg_power','acct_low_avg_power',
      'acct_avg_power_w4lj', 'acct_edp', 'acct_ed2p', 'acct_pdp',
    ],
  },
  fastsim: {
    policies: [...defaultPolices],
  },
  scheduleflow: {
    policies: [...defaultPolices],
  },
}

export const backfills = ['firstfit', 'bestfit', 'greedy', 'easy', 'conservative']

export type SchedulerType = keyof typeof schedulers

// TODO: It might be a good idea to use https://openapi-generator.tech/ to generate these models
// Note this type isn't entirely the same as on the server. I've only included the fields we use in
// the simulation server, and made them required so its more convenient to access them in the forms.
export interface SimulationConfig {
  system: string;
  cooling: boolean;
  // simulate_network?: boolean;
  weather: boolean;
  start: string;
  end: string;
  // time?: string; // just use start/end instead
  // fastforward?: string;
  time_delta: string;
  // time_unit?: string;
  numjobs?: number;
  // uncertainties?: boolean;
  seed?: number;
  // encrypt?: boolean;
  // power_scope?: "node" | "chip";
  // jid?: string;
  // scale?: number;
  // live?: boolean;
  workload: WorkloadType;
  replay: boolean;
  // multimodal?: number[];
  // jobsize_distribution?: ("uniform" | "weibull" | "normal")[] | null;
  // jobsize_normal_mean?: number | null;
  // jobsize_normal_stddev?: number | null;
  // jobsize_weibull_shape?: number | null;
  // jobsize_weibull_scale?: number | null;
  // jobsize_is_of_degree?: number | null;
  // jobsize_is_power_of?: number | null;
  // walltime_distribution?: ("uniform" | "weibull" | "normal")[] | null;
  // walltime_normal_mean?: number | null;
  // walltime_normal_stddev?: number | null;
  // walltime_weibull_shape?: number | null;
  // walltime_weibull_scale?: number | null;
  // cpuutil_distribution?: ("uniform" | "weibull" | "normal")[];
  // cpuutil_normal_mean?: number | null;
  // cpuutil_normal_stddev?: number | null;
  // cpuutil_weibull_shape?: number | null;
  // cpuutil_weibull_scale?: number | null;
  // gpuutil_distribution?: ("uniform" | "weibull" | "normal")[];
  // gpuutil_normal_mean?: number | null;
  // gpuutil_normal_stddev?: number | null;
  // gpuutil_weibull_shape?: number | null;
  // gpuutil_weibull_scale?: number | null;
  // gantt_nodes?: boolean;
  scheduler: SchedulerType;
  policy: string;
  // backfill?: string;
  arrival: "prescribed" | "poisson";
  // job_arrival_time?: number | null;
  // job_arrival_rate?: number | null;
  // accounts?: boolean;
  // accounts_json?: string | null;
  // downtime_first?: string | null;
  // downtime_interval?: string | null;
  // downtime_length?: string | null;
  // continuous_job_generation?: boolean;
  // maxqueue?: number;
  // filter?: string | null;
}


export function getDefaultSimulationConfig(): SimulationConfig {
  const startDate = new Date();
  startDate.setMilliseconds(0);
  startDate.setSeconds(0);
  const endDate = addHours(startDate, 1);

  return {
    system: "frontier",
    start: startDate.toISOString(),
    end: endDate.toISOString(),
    time_delta: "PT1S",
    cooling: false,
    weather: false,
    workload: "random",
    replay: false,
    numjobs: undefined,
    seed: undefined,
    scheduler: "default",
    policy: "fcfs",
    arrival: "prescribed",
  }
}
