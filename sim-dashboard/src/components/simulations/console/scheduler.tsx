import { SimulationStatistic } from "../../../models/SimulationStatistic.model";
import { ConsoleHeader } from "../../shared/simulation/consoleHeader";

export function Scheduler({
  statistics,
}: {
  statistics: SimulationStatistic;
}) {
  return (
    <div className="col-start-8 col-end-13 row-start-1 row-end-2">
      <ConsoleHeader>Scheduler Stats</ConsoleHeader>
      <div className="grid grid-cols-3 text-center dark:text-neutral-200">
        <span className="border-2 border-neutral-400 bg-neutral-300 text-purple-500 dark:border-neutral-900 dark:bg-neutral-700">
          Jobs Running
        </span>
        <span className="border-2 border-l-0 border-neutral-400 bg-neutral-300 text-purple-500 dark:border-neutral-900 dark:bg-neutral-700">
          Jobs Queued
        </span>
        <span className="border-2 border-l-0 border-neutral-400 bg-neutral-300 text-purple-500 dark:border-neutral-900 dark:bg-neutral-700">
          Down Nodes
        </span>
        <span className="border-2 border-t-0 border-neutral-400 dark:border-neutral-900">
          {statistics.jobs_running}
        </span>
        <span className="border-2 border-l-0 border-t-0 border-neutral-400 dark:border-neutral-900">
          {statistics.jobs_pending}
        </span>
        <span className="border-2 border-l-0 border-t-0 border-neutral-400 dark:border-neutral-900">
          {statistics.down_nodes.length}
        </span>
      </div>
    </div>
  );
}
