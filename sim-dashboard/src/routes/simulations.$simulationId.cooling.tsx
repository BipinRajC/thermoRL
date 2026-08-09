import { createFileRoute } from "@tanstack/react-router";
import { sumBy } from "lodash"
import {
  simulationConfigurationQueryOptions,
  simulationCoolingCDUQueryOptions,
} from "../util/queryOptions";
import { useQuery } from "@tanstack/react-query";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { Graph } from "../components/shared/plots/graph";
import { TimeStepBar } from "../components/cooling/timeStepBar";
import { useContext } from "react";
import { AppContext } from "../App";
import colors from "tailwindcss/colors";

type CoolingSearch = {
  resolution?: number;
  granularity?: number;
};

export const Route = createFileRoute("/simulations/$simulationId/cooling")({
  component: SimulationCooling,
  validateSearch: (search: Record<string, unknown>): CoolingSearch => {
    return {
      resolution: Number(search.resolution) || undefined,
      granularity: Number(search.granularity) || undefined,
    };
  },
});

function SimulationCooling() {
  const { theme } = useContext(AppContext);
  const { simulationId } = Route.useParams();
  const { granularity, resolution } = Route.useSearch();

  const { data: sim } = useQuery(simulationConfigurationQueryOptions(simulationId))

  const { data, isLoading } = useQuery(
    simulationCoolingCDUQueryOptions(simulationId, {
      granularity: granularity,
      resolution: granularity ? undefined : resolution, // granularity will override resolution
    }),
  );

  return (
    <div className={`flex-1 overflow-y-auto dark:[color-scheme:dark]`}>
      <TimeStepBar />
      {!sim || !data || isLoading ? (
        <LoadingSpinner />
      ) : (
        <div
          className={`pr-2 ${theme === "light" ? "bg-white" : "bg-transparent"}`}
        >
          <Graph
            key="Total Power Usage Graph"
            data={[
              {
                x: data.data.map(d => d.timestamp),
                y: data.data.map(d => sumBy(d.cdus, d => d.total_power)),
                type: "scatter",
                mode: "lines+markers",
                hovertemplate: "%{x}<br />Power: %{y} kW<extra></extra>",
                yaxis: "y",
                line: {
                  shape: "linear",
                  smoothing: 1.3,
                },
              },
            ]}
            layout={{
              title: "Total Power Usage",
              xaxis: {
                title: { text: "Time" },
                range: [sim.start, sim.end],
              },
              yaxis: {
                title: { text: "Power (kW)", standoff: 20 },
                type: "linear",
              },
            }}
          />
          <Graph
            key="Total Power Loss Graph"
            data={[
              {
                x: data.data.map(d => d.timestamp),
                y: data.data.map(d => sumBy(d.cdus, d => d.total_loss)),
                type: "scatter",
                mode: "lines+markers",
                hovertemplate: "%{x}<br />Power: %{y} kW<extra></extra>",
                line: {
                  shape: "linear",
                  smoothing: 1.3,
                },
              },
            ]}
            layout={{
              title: "Total Power Loss",
              xaxis: {
                title: { text: "Time" },
                range: [sim.start, sim.end],
              },
              yaxis: { title: { text: "Power (kW)", standoff: 20 } },
            }}
          />
          <Graph
            key="Average Rack Temp Graph"
            data={[
              {
                x: data.data.map(d => d.timestamp),
                y: data.data.map(d => sumBy(d.cdus, d => d.rack_return_temp ?? 0) / d.cdus.length),
                type: "scatter",
                mode: "lines+markers",
                hovertemplate:
                  "%{x}<br />Average Rack Return Temperature: %{y} °C<extra></extra>",
                line: {
                  shape: "linear",
                  smoothing: 1.3,
                },
                name: "Return Temperature",
              },
              {
                x: data.data.map(d => d.timestamp),
                y: data.data.map(d => sumBy(d.cdus, d => d.rack_supply_temp ?? 0) / d.cdus.length),
                type: "scatter",
                mode: "lines+markers",
                hovertemplate:
                  "%{x}<br />Average Rack Supply Temperature: %{y} °C<extra></extra>",
                hoverlabel: { font: { color: colors.white } },
                line: {
                  shape: "linear",
                  smoothing: 1.3,
                },
                name: "Supply Temperature",
              },
            ]}
            layout={{
              title: "Average Rack Temperatures",
              xaxis: {
                title: { text: "Time" },
                range: [sim.start, sim.end],
              },
              yaxis: { title: { text: "Temperature (°C)", standoff: 20 } },
            }}
          />
          <Graph
            key="Average Flowrate Graph"
            data={[
              {
                x: data.data.map(d => d.timestamp),
                y: data.data.map(d => sumBy(d.cdus, d => d.rack_flowrate ?? 0) / d.cdus.length),
                type: "scatter",
                mode: "lines+markers",
                hovertemplate:
                  "%{x}<br />Average Rack Flowrate: %{y} gpm<extra></extra>",
                line: {
                  shape: "linear",
                  smoothing: 1.3,
                },
              },
            ]}
            layout={{
              title: "Average Rack Flowrate",
              xaxis: {
                title: { text: "Time" },
                range: [sim.start, sim.end],
              },
              yaxis: { title: { text: "Flowrate (gpm)", standoff: 20 } },
            }}
          />
        </div>
      )}
    </div>
  );
}
