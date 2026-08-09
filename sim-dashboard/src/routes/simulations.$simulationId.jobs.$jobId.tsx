import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Modal } from "../components/shared/modal";
import {
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { ListResponse } from "../util/queryOptions";
import { Job, JobPower } from "../models/Job.model";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { useState } from "react";
import Box from "../components/shared/simulation/box";
import { formatDate } from "../util/datetime";
//import { Graph } from "../components/shared/plots/graph";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const Route = createFileRoute("/simulations/$simulationId/jobs/$jobId")({
  component: JobModal,
});

function JobModal() {
  const navigate = useNavigate({ from: Route.fullPath });
  const { jobId, simulationId } = Route.useParams();
  const [search, setSearch] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["simulation", "jobs", simulationId, "job", jobId],
    queryFn: async () => {
      const res = await axios.get<ListResponse<Job>>(
        `/simulation/${simulationId}/scheduler/jobs?job_id=eq:${jobId}`,
      );

      return res.data;
    },
    select: (data) => {
      if (data.results.length > 0) {
        return data.results[0];
      }
    },
  });

  const { data: jobPower, isLoading: isLoadingPowerHistory } = useQuery({
    queryKey: ["simulation", "jobs", simulationId, "job", jobId, "power"],
    queryFn: async () => {
      const res = await axios.get<{
        granularity: number;
        start: string;
        end: string;
        data: JobPower[];
      }>(
        `/simulation/${simulationId}/scheduler/jobs/${jobId}/power-history`,
      );
      return res;
    },
  });

  return (
    <Modal open={!!jobId}>
      <header className="flex items-center justify-between border-b-2 px-4 py-2">
        <span className="text-lg font-medium">Job Details</span>
        <button
          onClick={(e) => {
            e.preventDefault();
            navigate({
              to: "/simulations/$simulationId/jobs",
              params: { simulationId: simulationId },
              search: (prev) => ({ ...prev }),
            });
          }}
          className="transition-opacity duration-500 hover:opacity-50"
        >
          <XMarkIcon className="h-6 w-6" />
        </button>
      </header>
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <LoadingSpinner />
        </div>
      ) : isError || !data ? (
        <div className="flex flex-1 flex-col items-center justify-center">
          <ExclamationTriangleIcon className="h-8 w-8" />
          <h1>Error Loading Job with ID: {jobId}</h1>
        </div>
      ) : (
        <section className="flex flex-wrap gap-8 overflow-auto p-4">
          <Box>
            <Box.Header>Job Id</Box.Header>
            <Box.Value>{data.job_id}</Box.Value>
          </Box>
          <Box>
            <Box.Header>State</Box.Header>
            <Box.Value>{data.state_current}</Box.Value>
          </Box>
          <Box>
            <Box.Header>Time Submitted</Box.Header>
            <Box.Value>{formatDate(data.time_submission)}</Box.Value>
          </Box>
          <Box>
            <Box.Header>Time Range</Box.Header>
            <Box.Value>
              {formatDate(data.time_start)} -{" "}
              {data.time_end
                ? formatDate(data.time_end)
                : "Unfinished"}
            </Box.Value>
          </Box>
          <Box>
            <Box.Header>Node Count</Box.Header>
            <Box.Value>{data.node_count}</Box.Value>
          </Box>
          <Box>
            <Box.Header>Nodes</Box.Header>
            <input
              placeholder="Search..."
              onChange={(e) => {
                e.preventDefault();
                setSearch(e.target.value);
              }}
              value={search}
              className="rounded-md border-2 bg-transparent px-3 py-1 text-black focus:outline-none dark:text-neutral-200"
            />
            <div className="mt-2 flex max-h-64 w-full flex-col overflow-auto px-8">
              {data.nodes
                .filter((node) => (search ? node.includes(search) : true))
                .map((node) => (
                  <span key={node}>{node}</span>
                ))}
            </div>
          </Box>
          <div className="flex-1">
            {isLoadingPowerHistory ? (
              <LoadingSpinner />
            ) : (
              // <Graph
              //   key="Power Usage Graph"
              //   data={[
              //     {
              //       x: jobPower?.data.data.map((result) => result.timestamp),
              //       y: jobPower?.data.data.map((result) => result.power),
              //       type: "scatter",
              //       mode: "lines+markers",
              //       hovertemplate: "%{x}<br />Power: %{y} kW<extra></extra>",
              //       yaxis: "y",
              //       line: {
              //         shape: "linear",
              //         smoothing: 1.3,
              //       },
              //     },
              //   ]}
              //   layout={{
              //     title: "Power Usage",
              //     xaxis: { title: { text: "Time" }, type: "date" },
              //     yaxis: {
              //       title: { text: "Power (kW)", standoff: 20 },
              //       type: "linear",
              //     },
              //   }}
              // />
              <ResponsiveContainer>
                <LineChart data={jobPower?.data.data ?? []}>
                  <CartesianGrid strokeDasharray={"3 3"} />
                  <XAxis dataKey={"timestamp"} />
                  <YAxis />
                  <Tooltip />
                  <Line dataKey={"power"} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>
      )}
    </Modal>
  );
}
