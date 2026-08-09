import { createFileRoute } from "@tanstack/react-router";
import { simulationConfigurationQueryOptions } from "../util/queryOptions";
import { useQuery } from "@tanstack/react-query";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { JobList } from "../components/jobs/JobList";
import { headers as JobColumns } from "../components/jobs/list/JobListColumns";
import { ArrowDownTrayIcon } from "@heroicons/react/24/outline";
import { operatorCombinator, sortCombinator } from "../util/filterCombinator";
import { toDate } from "date-fns";
import { cloneDeep } from "lodash";
import { useState } from "react";
import { Tooltip } from "react-tooltip";
import { JobListFilterModal } from "../components/jobs/list/JobListFilterModal";
import { useJobReplay } from "../util/hooks/useReplay";
import { SortDirection } from "../models/filters/sortDetails.model";

export const Route = createFileRoute("/simulations/$simulationId/jobs")({
  component: SimulationJobs,
});

function SimulationJobs() {
  const { simulationId } = Route.useParams();
  const search = Route.useSearch();
  const currentTimestamp = search.currentTimestamp ? toDate(search.currentTimestamp) : undefined;

  const [columns, setColumns] = useState(cloneDeep(JobColumns));

  const { data: sim } = useQuery(simulationConfigurationQueryOptions(simulationId));

  const { data: jobs, totalResults, fetchNextPage, hasNextPage } = useJobReplay({
    sim: sim,
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
    sort: sortCombinator(columns),
    filters: operatorCombinator(columns),
  })

  const onSort = (columnName: string, direction: SortDirection) => {
    const updatedColumns = cloneDeep(columns);
    const currentColumn = updatedColumns.find(
      (column) => column.name === columnName,
    );

    if (currentColumn) {
      currentColumn.sort.direction = direction;
    }

    setColumns(updatedColumns);
  };

  if (!jobs) {
    return <LoadingSpinner />;
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-end gap-4 px-4 py-4">
        <button
          className="rounded-full px-2 py-2 transition-colors duration-500 hover:bg-neutral-300 dark:text-neutral-200 dark:hover:bg-neutral-700"
          data-tooltip-id="download-tooltip"
          data-tooltip-content={"Export to CSV"}
          data-tooltip-delay-show={500}
        >
          <ArrowDownTrayIcon className="h-6 w-6" />
        </button>
        <JobListFilterModal columns={columns} setColumns={setColumns} />
        <Tooltip id="download-tooltip" />
      </div>
      <JobList
        jobs={jobs}
        columns={columns}
        totalJobs={totalResults}
        fetchNextPage={fetchNextPage}
        hasNextPage={hasNextPage}
        onSort={onSort}
      />
    </div>
  );
}
