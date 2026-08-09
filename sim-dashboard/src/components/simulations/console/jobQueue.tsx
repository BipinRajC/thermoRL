import { Job } from "../../../models/Job.model";
import { ConsoleHeader } from "../../shared/simulation/consoleHeader";

export function JobQueue({ jobs }: { jobs: Job[] }) {
  return (
    <div className="col-start-8 col-end-13 row-start-2 row-end-12 flex flex-col overflow-hidden">
      <ConsoleHeader>Job Queue</ConsoleHeader>
      <div className="overflow-auto border-2 border-neutral-400 text-center text-sm dark:border-neutral-900">
        <div className="grid grid-cols-4 border-b-2 border-neutral-400 bg-neutral-300 text-xs text-purple-500 dark:border-neutral-900 dark:bg-neutral-700">
          <span className="border-r-2 border-neutral-400 dark:border-neutral-900">
            Job Id
          </span>
          <span className="border-r-2 border-neutral-400 dark:border-neutral-900">
            Name
          </span>
          <span className="border-r-2 border-neutral-400 dark:border-neutral-900">
            State
          </span>
          <span>Nodes</span>
        </div>
        {jobs.map((job) => (
          <div
            className="grid grid-cols-4 dark:text-neutral-200"
            key={job.job_id}
          >
            <span className="border-r-2 border-neutral-400 dark:border-neutral-900">
              {job.job_id}
            </span>
            <span
              className="overflow-hidden text-ellipsis whitespace-nowrap border-r-2 border-neutral-400 px-2 dark:border-neutral-900"
              title={job.name}
            >
              {job.name}
            </span>
            <span className="border-r-2 border-neutral-400 dark:border-neutral-900">
              {job.state_current.charAt(0)}
            </span>
            <span>{job.node_count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
