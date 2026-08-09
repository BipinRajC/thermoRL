import { createFileRoute } from "@tanstack/react-router";
import { formatDate } from "../util/datetime";
import * as iso8601 from "iso8601-duration";
import { useSuspenseQuery } from "@tanstack/react-query";
import { simulationConfigurationQueryOptions } from "../util/queryOptions";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { Section } from "../components/shared/simulation/section";
import Box from "../components/shared/simulation/box";

export const Route = createFileRoute(
  "/simulations/$simulationId/configuration",
)({
  component: SimulationConfiguration,
  loader: (opts) =>
    opts.context.queryClient.ensureQueryData(
      simulationConfigurationQueryOptions(opts.params.simulationId),
    ),
});

function SimulationConfiguration() {
  const { simulationId } = Route.useParams();
  const { data, isLoading } = useSuspenseQuery(
    simulationConfigurationQueryOptions(simulationId),
  );

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-8 py-8 dark:[color-scheme:dark]">
      <Section header="Status">
        <Box>
          <Box.Header>State</Box.Header>
          <Box.Value>
            {data.state.charAt(0).toLocaleUpperCase() + data.state.slice(1)}
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Progress</Box.Header>
          <div className="group relative h-8 w-full rounded-full border-2 border-neutral-400 dark:border-neutral-900">
            <div
              className={`absolute left-0 top-0 flex h-full items-center justify-end rounded-full bg-blue-500 px-4 ${data.progress === 1 && `bg-green-500`}`}
              style={{ width: `${data.progress * 100}%` }}
            />
            <span
              className={`absolute right-3 z-10 text-white dark:text-neutral-200`}
            >
              {data.progress === 1
                ? "Complete"
                : `${(data.progress * 100).toFixed(1)}%`}
            </span>
          </div>
        </Box>
        {data.state == "fail" ? (
          <Box>
            <Box.Header>Errors</Box.Header>
            <Box.Value>{data.error_messages}</Box.Value>
          </Box>
        ) : null}
      </Section>
      <Section header="General">
        <Box>
          <Box.Header>System</Box.Header>
          <Box.Value>{data.system}</Box.Value>
        </Box>
        <Box>
          <Box.Header>User</Box.Header>
          <Box.Value>{data.user}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Logical Start</Box.Header>
          <Box.Value>{formatDate(data.start)}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Logical End</Box.Header>
          <Box.Value>{formatDate(data.end)}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Run Start</Box.Header>
          <Box.Value>{formatDate(data.execution_start)}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Run End</Box.Header>
          <Box.Value>
            {data.execution_end
              ? formatDate(data.execution_end)
              : "-"}
          </Box.Value>
        </Box>
      </Section>
      <Section header="RAPS Configuration">
        <Box>
          <Box.Header>Workload Mode</Box.Header>
          <Box.Value>
            {data.config.workload}
          </Box.Value>
        </Box>
        {data.config.workload ? (
          <>
            <Box>
              <Box.Header>Number of Jobs</Box.Header>
              <Box.Value>
                {data.config.numjobs?.toString() || "-"}
              </Box.Value>
            </Box>
            <Box>
              <Box.Header>Seed for Randomizer</Box.Header>
              <Box.Value>
                {data.config.seed?.toString() || "-"}
              </Box.Value>
            </Box>
          </>
        ) : null}
        <Box>
            <Box.Header>Scheduler</Box.Header>
            <Box.Value>
              {data.config.scheduler}
            </Box.Value>
        </Box>
        <Box>
            <Box.Header>Schedule Policy</Box.Header>
            <Box.Value>
              {data.config.policy}
            </Box.Value>
        </Box>
        <Box>
            <Box.Header>Reschedule Arrival</Box.Header>
            <Box.Value>
              {data.config.arrival}
            </Box.Value>
        </Box>
        <Box>
          <Box.Header>Time Delta</Box.Header>
          <Box.Value>{iso8601.toSeconds(iso8601.parse(data.config.time_delta))}</Box.Value>
        </Box>
      </Section>
      <Section header="Cooling Configuration">
        <Box>
          <Box.Header>Enabled</Box.Header>
          <Box.Value>
            {data.config.cooling.toString()}
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Weather</Box.Header>
          <Box.Value>
            {data.config.weather.toString()}
          </Box.Value>
        </Box>
      </Section>
    </div>
  );
}
