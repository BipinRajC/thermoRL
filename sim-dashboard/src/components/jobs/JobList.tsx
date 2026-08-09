import { ReactNode, useEffect, useRef } from "react";
import { defaultRangeExtractor, useVirtualizer } from "@tanstack/react-virtual";
import { Job } from "../../models/Job.model";
import { formatDate } from "../../util/datetime";
import { JobListHeader } from "./list/JobListHeader";
import { ColumnHeader } from "../../models/dataGrid/columnHeader.model";
import { GridSizes, getGridSize } from "../../util/gridSizing";
import { FetchNextPageOptions } from "@tanstack/react-query";
import { Outlet, useNavigate } from "@tanstack/react-router";
import { Route as JobsRoute } from "../../routes/simulations.$simulationId.jobs";
import { computeJobState } from "../../util/jobs"
import { SortDirection } from "../../models/filters/sortDetails.model";

function JobListColumn({
  size,
  children,
  noBorder,
}: {
  size: GridSizes;
  children: ReactNode;
  noBorder?: boolean;
}) {
  return (
    <div
      className={`flex-auto overflow-hidden text-ellipsis text-nowrap dark:text-neutral-200 ${getGridSize(size)} flex h-full items-center justify-center border-neutral-400 px-1 dark:border-neutral-900 ${noBorder ? "border-r-0" : "border-r-2"}`}
      title={children?.toString()}
    >
      <span className="overflow-hidden text-ellipsis text-nowrap">
        {children}
      </span>
    </div>
  );
}

export function JobList({
  jobs,
  columns,
  totalJobs,
  fetchNextPage,
  hasNextPage,
  onSort,
}: {
  jobs: Job[];
  columns: ColumnHeader[],
  totalJobs: number;
  fetchNextPage: (options?: FetchNextPageOptions | undefined) => void;
  hasNextPage: boolean;
  onSort: (columnName: string, direction: SortDirection) => void;
}) {
  const navigate = useNavigate({ from: JobsRoute.fullPath });
  const { simulationId } = JobsRoute.useParams();
  const { currentTimestamp } = JobsRoute.useSearch();
  const rows: (ColumnHeader[] | Job)[] = [columns, ...jobs];

  const parentRef = useRef(null);

  const rowVirtualizer = useVirtualizer({
    count: hasNextPage ? rows.length + 1 : rows.length,
    estimateSize: () => 50,
    getScrollElement: () => parentRef.current,
    rangeExtractor: (range) => {
      const newRows = new Set([0, ...defaultRangeExtractor(range)]);
      return [...newRows];
    },
  });

  useEffect(() => {
    const [lastItem] = [...rowVirtualizer.getVirtualItems()].reverse();

    if (!lastItem) {
      return;
    }

    if (
      lastItem.index >= rows.length - 1 &&
      hasNextPage
    ) {
      fetchNextPage();
    }
  }, [
    hasNextPage,
    fetchNextPage,
    rows.length,
    rowVirtualizer.getVirtualItems(),
  ]);

  return (
    <>
      <Outlet />
      <div className="flex flex-1 flex-col overflow-hidden bg-transparent">
        <div
          ref={parentRef}
          className="flex-1 overflow-auto dark:[color-scheme:dark]"
        >
          <div
            className="relative w-full"
            style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualItem) => {
              const job = rows[virtualItem.index];

              if (virtualItem.index === 0 && Array.isArray(job)) {
                return (
                  <JobListHeader
                    headers={job}
                    key={virtualItem.key}
                    style={{
                      height: `${virtualItem.size}px`,
                      transform: `translateY(${virtualItem.start}px)`,
                    }}
                    onSort={onSort}
                  />
                );
              } else if (!Array.isArray(job) && job) {
                return (
                  <div
                    key={virtualItem.key}
                    className={`absolute left-0 top-0 grid w-full cursor-pointer grid-cols-12 items-center border-b-2 border-neutral-400 bg-transparent transition-opacity duration-500 hover:opacity-50 dark:border-neutral-900`}
                    style={{
                      height: `${virtualItem.size}px`,
                      transform: `translateY(${virtualItem.start}px)`,
                    }}
                    onClick={(e) => {
                      e.preventDefault();
                      navigate({
                        to: "/simulations/$simulationId/jobs/$jobId",
                        params: {
                          simulationId: simulationId,
                          jobId: job.job_id,
                        },
                        search: (prev) => ({ ...prev }),
                      });
                    }}
                  >
                    <JobListColumn size="small">{job.job_id}</JobListColumn>
                    <JobListColumn size="small">{job.name}</JobListColumn>
                    <JobListColumn size="small">
                      {computeJobState(job, currentTimestamp)}
                    </JobListColumn>
                    <JobListColumn size="small">{job.node_count}</JobListColumn>
                    <JobListColumn size="large">
                      {formatDate(job.time_submission)}
                    </JobListColumn>
                    <JobListColumn size="small">{job.time_limit}</JobListColumn>
                    <JobListColumn size="medium">
                      {formatDate(job.time_start)}
                    </JobListColumn>
                    <JobListColumn size="medium" noBorder>
                      {formatDate(job.time_end)}
                    </JobListColumn>
                  </div>
                );
              } else if (virtualItem.index < totalJobs) {
                return (
                  <span
                    key={virtualItem.key}
                    className="absolute left-0 top-0 flex w-full items-center justify-center gap-4 self-center px-4 py-2 transition-opacity duration-500 hover:opacity-50 dark:text-neutral-200"
                    style={{
                      height: `${virtualItem.size}px`,
                      transform: `translateY(${virtualItem.start}px)`,
                    }}
                  >
                    <svg
                      aria-hidden="true"
                      className="h-5 w-5 animate-spin fill-blue-500 text-gray-200 dark:text-gray-600"
                      viewBox="0 0 100 101"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
                        fill="currentColor"
                      />
                      <path
                        d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
                        fill="currentFill"
                      />
                    </svg>
                    Loading Jobs...
                  </span>
                );
              } else {
                return null;
              }
            })}
          </div>
        </div>
      </div>
    </>
  );
}
