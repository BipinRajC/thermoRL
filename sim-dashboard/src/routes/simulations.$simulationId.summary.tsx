import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { toDate } from "date-fns";
import { simulationConfigurationQueryOptions } from "../util/queryOptions";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { Section } from "../components/shared/simulation/section";
import Box from "../components/shared/simulation/box";
import { Message } from "../components/shared/simulation/message";
import { SimulationGauges } from "../components/simulations/details/gauges";
import { useReplay } from "../util/hooks/useReplay";
import {
  simulationSystemStatsQueryOptions, simulationCoolingCDUQueryOptions,
  simulationCoolingCEPQueryOptions,
} from "../util/queryOptions"

export const Route = createFileRoute("/simulations/$simulationId/summary")({
  component: SimulationSummary,
});

function SimulationSummary() {
  const { simulationId } = Route.useParams();
  const search = Route.useSearch();
  const currentTimestamp = search.currentTimestamp ? toDate(search.currentTimestamp) : undefined;
  const { data: sim } = useQuery(simulationConfigurationQueryOptions(simulationId));

  const { data: schedulerStatistics } = useReplay({
    sim: sim,
    query: (params) => simulationSystemStatsQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })

  const { data: cdus } = useReplay({
    sim: sim,
    query: (params) => simulationCoolingCDUQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })

  const { data: cep } = useReplay({
    sim: sim,
    query: (params) => simulationCoolingCEPQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-8 py-8">
      <Section header="Metrics" sectionProps={{ className: "grid-cols-3" }}>
        {(sim && cdus && schedulerStatistics) ? (
          <SimulationGauges
            sim={sim}
            cdus={cdus.cdus}
            statistics={schedulerStatistics}
            cep={cep}
          />
        ) : (sim && sim.progress_date == sim.start) ? (
            <Message>No data available {sim.state == 'running' ? 'yet' : ''}</Message>
        ) : (
          <LoadingSpinner/>
        )}
      </Section>
      <Section header={!currentTimestamp ? "Final Projections" : "Latest Projections"}>
        <Box>
          <Box.Header>Jobs Pending</Box.Header>
          <Box.Value>{schedulerStatistics?.jobs_pending ?? "-"}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Jobs Running</Box.Header>
          <Box.Value>{schedulerStatistics?.jobs_running ?? "-"}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Jobs Completed</Box.Header>
          <Box.Value>{schedulerStatistics?.jobs_completed ?? "-"}</Box.Value>
        </Box>
        <Box>
          <Box.Header>Job Throughput</Box.Header>
          <Box.Value>{schedulerStatistics?.throughput ?? "-"} Jobs/Hr</Box.Value>
        </Box>
        <Box>
          <Box.Header>Average Power Usage</Box.Header>
          <Box.Value>
            {schedulerStatistics?.average_power
              ? schedulerStatistics.average_power / 1000
              : "-"}{" "}
            kW
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Average Power Loss</Box.Header>
          <Box.Value>
            {schedulerStatistics?.average_loss
              ? schedulerStatistics.average_loss / 1000
              : "-"}{" "}
            kW
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Total Energy Consumed</Box.Header>
          <Box.Value>
            {schedulerStatistics?.total_energy_consumed ?? "-"} MW-hr
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>System Power Efficiency</Box.Header>
          <Box.Value>
            {schedulerStatistics?.system_power_efficiency ?? "-"}%
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Carbon Emissions</Box.Header>
          <Box.Value>
            {schedulerStatistics?.carbon_emissions ?? "-"} Metric Tons of CO2
          </Box.Value>
        </Box>
        <Box>
          <Box.Header>Total Cost</Box.Header>
          <Box.Value>
            {schedulerStatistics?.total_cost
              ? Intl.NumberFormat("en-US", {
                  currency: "USD",
                  style: "currency",
                }).format(schedulerStatistics.total_cost)
              : "-"}
          </Box.Value>
        </Box>
      </Section>
    </div>
  );
}
