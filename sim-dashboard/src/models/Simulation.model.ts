import { SimulationConfig } from "./SimulationConfig.model";

export interface Simulation {
  id: string;
  user: string;
  system: string;
  state: "running" | "success" | "fail";
  error_messages: string|null;
  start: string;
  end: string;
  execution_start: string;
  execution_end: string | null;
  progress: number;
  progress_date: string;
  config: SimulationConfig;
}
