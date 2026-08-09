export interface Job {
  job_id: string;
  name: string;
  node_count: number;

  /**
   * ISO Datetime string
   */
  time_snapshot: string;

  /**
   * ISO Datetime string
   */
  time_submission: string;

  time_limit: number;

  /**
   * ISO Datetime string
   */
  time_start: string;

  /**
   * ISO Datetime string
   */
  time_end: string|null;

  state_current:
    | "COMPLETED"
    | "PENDING"
    | "RUNNING"
    | "CANCELLED"
    | "FAILED"
    | "TIMEOUT";

  nodes: string[];
}

export interface JobPower {
  timestamp: string;
  power: number;
}
