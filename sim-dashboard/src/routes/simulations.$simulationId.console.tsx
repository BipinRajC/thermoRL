import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PressureFlowRate } from "../components/simulations/console/pressureFlowRate";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { JobQueue } from "../components/simulations/console/jobQueue";
import { CDUList } from "../components/simulations/console/cduList";
import { Power } from "../components/simulations/console/power";
import { Scheduler } from "../components/simulations/console/scheduler";
import { Message } from "../components/shared/simulation/message";
import { toDate } from "date-fns";
import {
  simulationConfigurationQueryOptions, simulationSystemStatsQueryOptions,
  simulationCoolingCDUQueryOptions, simulationCoolingCEPQueryOptions,
} from "../util/queryOptions";
import { useReplay, useJobReplay } from "../util/hooks/useReplay";


export const Route = createFileRoute("/simulations/$simulationId/console")({
  component: SimulationConsoleView,
});

function SimulationConsoleView() {
  const { simulationId } = Route.useParams();
  const search = Route.useSearch();
  const currentTimestamp = search.currentTimestamp ? toDate(search.currentTimestamp) : undefined;

  const { data: sim } = useQuery(simulationConfigurationQueryOptions(simulationId))

  const { data: schedulerStatistics } = useReplay({
    sim: sim,
    query: (params) => simulationSystemStatsQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })
  
  const { data: cdus, isLoading: cdusIsLoading } = useReplay({
    sim: sim,
    query: (params) => simulationCoolingCDUQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })
  
  const { data: cep, isLoading: cepIsLoading } = useReplay({
    sim: sim,
    query: (params) => simulationCoolingCEPQueryOptions(simulationId, params),
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })

  const { data: jobs, isLoading: jobsIsLoading } = useJobReplay({
    sim: sim,
    timestamp: currentTimestamp,
    stepInterval: search.playbackInterval,
    summarize: !currentTimestamp,
  })

  return (
    <section className="grid min-w-[1024px] grid-cols-12 gap-2 overflow-auto p-2">
      {(sim && sim.progress_date == sim.start) ? (
        <Message>No data available {sim.state == 'running' ? 'yet' : ''}</Message>
      ) : (<>
        {!cdusIsLoading ? (
          <PressureFlowRate metrics={cdus?.cdus} />
        ): (<LoadingSpinner/>)}
        {!jobsIsLoading ? (
          <JobQueue jobs={jobs} />
        ) : (<LoadingSpinner/>)}
        {!cdusIsLoading ? (
          <CDUList metrics={cdus?.cdus} />
        ) : (<LoadingSpinner/>)}
        {!cdusIsLoading && !cepIsLoading ? (
          <Power cdus={cdus?.cdus} cep={cep}/>
        ) : (<LoadingSpinner/>)}
        {schedulerStatistics ? (
          <Scheduler statistics={schedulerStatistics} />
        ) : (<LoadingSpinner/>)}
      </>)}
    </section>
  );
}
