import {
  ArrowLeftIcon,
  ArrowPathIcon,
  PauseIcon,
  PlayIcon,
} from "@heroicons/react/24/outline";
import {
  Link, LinkProps, Outlet, createFileRoute, useNavigate, Navigate,
} from "@tanstack/react-router";
import { BaseSyntheticEvent, useState } from "react";
import { Tooltip } from "react-tooltip";
import { Timeline } from "../components/simulations/details/timeline";
import { differenceInSeconds, isEqual as isDateEqual } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { simulationConfigurationQueryOptions } from "../util/queryOptions";
import { LoadingSpinner } from "../components/shared/loadingSpinner";
import { useInterval } from "../util/hooks/misc";
import { getMaxTimestamp, snapReplayTimestamp } from "../util/hooks/useReplay"
import { formatDate } from "../util/datetime";


type SearchParams = {
  currentTimestamp?: string,
  playbackInterval: number,
}


export const Route = createFileRoute("/simulations/$simulationId")({
  component: Simulation,
  validateSearch: (search: Record<string, unknown>): SearchParams => {
    return {
      currentTimestamp: search.currentTimestamp as string|undefined,
      playbackInterval: (search.playbackInterval as number) || 15,
    };
  },
});

function TabLink(props: LinkProps) {
  return (
    <Link
      className="flex flex-1 items-center justify-center border-b-2 px-4 py-4 transition-all duration-500 hover:border-b-blue-300 hover:opacity-80 dark:text-neutral-200"
      activeProps={{
        className: "border-blue-500 font-medium hover:border-b-blue-500",
      }}
      inactiveProps={{
        className: "border-neutral-400",
      }}
      {...props}
    >
      {props.children}
    </Link>
  );
}

function Simulation() {
  const navigate = useNavigate({ from: Route.fullPath });
  const updateSearchParams = (params: Partial<SearchParams>) => {
    navigate({
      search: (prev) => ({ ...prev, ...params }),
      replace: false,
    });
  }

  const { simulationId } = Route.useParams();
  const search = Route.useSearch();
  const { data, isLoading } = useQuery(
    simulationConfigurationQueryOptions(simulationId),
  );

  const [replayStatus, setReplayStatus] = useState<"play" | "pause" | "summarize">(
    search.currentTimestamp ? "pause" : "summarize"
  );
  const [rate, setRate] = useState(20);

  const maxTimestamp = data ? getMaxTimestamp(data, search.playbackInterval) : undefined;
  const { currentTimestamp, nextTimestamp } = (data && search.currentTimestamp) ?
    snapReplayTimestamp(data, search.currentTimestamp, search.playbackInterval) : {}

  useInterval(() => {
    if (replayStatus == "play") {
      if (nextTimestamp) {
        updateSearchParams({currentTimestamp: nextTimestamp.toISOString()});
      } else if (data?.execution_end) {
        setReplayStatus("summarize")
        updateSearchParams({currentTimestamp: undefined});
      }
      // Just wait for the simulation to produce more data
    }
  }, (replayStatus == "play") ? 15000 / rate : null)

  const onReplayUpdate = (e: BaseSyntheticEvent) => {
    e.preventDefault();
    if (replayStatus === "play") {
      setReplayStatus("pause");
    } else {
      setReplayStatus("play");
    }
  };

  const onRestart = (e: BaseSyntheticEvent) => {
    e.preventDefault();
    if (data) {
      setReplayStatus("play");
      updateSearchParams({currentTimestamp: data.start});
    }
  };

  const onTimelineChange = (value: Date) => {
    setReplayStatus("pause");
    if (data) {
      const result = snapReplayTimestamp(data, value, search.playbackInterval);
      updateSearchParams({currentTimestamp: result.currentTimestamp.toISOString()});
    }
  };

  if (isLoading || !data || !maxTimestamp) {
    return <LoadingSpinner />;
  } else if (!search.currentTimestamp && !data.execution_end) {
    // If currentTimestamp is missing and the sim is still running, jump to playing the sim where it
    // is currently at. If the sim is complete, we'll summarize when currentTimestamp is undefined.
    return <Navigate
      params={{ simulationId: simulationId }}
      search={prev => ({
        ...prev,
        playbackInterval: search.playbackInterval,
        currentTimestamp: maxTimestamp.toISOString(), // will get snapped down if needed
      })}
    />
  }

  return (
    <div className="m-6 flex flex-1 flex-col justify-center overflow-hidden">
      <div className="flex items-center gap-12 dark:text-neutral-200">
        <Link
          to="/simulations"
          className="flex items-center gap-2 self-start transition-opacity duration-500 hover:opacity-75"
        >
          <ArrowLeftIcon className="h-6 w-6" />
          <span>Back to List</span>
        </Link>
        <span className="text-medium">Simulation ID: {simulationId}</span>
      </div>
      <div className="mt-4 flex flex-1 flex-col overflow-y-hidden rounded-md bg-neutral-200 shadow-md dark:bg-neutral-800">
        <div className="flex items-center">
          <TabLink
            to="/simulations/$simulationId/summary"
            params={{ simulationId: simulationId }}
            search={search}
          >
            Summary
          </TabLink>
          <TabLink
            to="/simulations/$simulationId/configuration"
            params={{ simulationId: simulationId }}
            search={search}
          >
            Configuration
          </TabLink>
          <TabLink
            to="/simulations/$simulationId/jobs"
            params={{ simulationId: simulationId }}
            search={search}
          >
            Jobs
          </TabLink>
          <TabLink
            to="/simulations/$simulationId/cooling"
            params={{ simulationId: simulationId }}
            search={{ ...search, granularity: 900 }}
          >
            Plots
          </TabLink>
          <TabLink
            to="/simulations/$simulationId/console"
            params={{ simulationId: simulationId }}
            search={{ ...search }}
          >
            Console
          </TabLink>
        </div>
        <Outlet />
      </div>
      <div className="mt-6 flex items-center gap-4">
        <button
          onClick={onRestart}
          disabled={currentTimestamp && isDateEqual(currentTimestamp, data.start)}
        >
          <ArrowPathIcon
            className={`h-6 w-6 text-neutral-400`}
            data-tooltip-id="restart-button"
            data-tooltip-content="Restart Simulation"
            data-tooltip-delay-show={750}
          />
        </button>
        <button
          onClick={onReplayUpdate}
          disabled={replayStatus !== "play" && isDateEqual(maxTimestamp, data.start)}
        >
          {replayStatus == "play" ? (
            <PauseIcon className={`h-6 w-6 text-neutral-400`} />
          ) : (
            <PlayIcon
              data-tooltip-id="play-button"
              data-tooltip-content="Play Simulation"
              data-tooltip-delay-show={750}
              className={`h-6 w-6 text-neutral-400`}
            />
          )} 
        </button>
        <span
          className="w-36 text-nowrap text-right text-neutral-400"
          data-tooltip-id="current-timestamp"
          data-tooltip-content={`${formatDate(currentTimestamp)} / ${formatDate(data.end)}`}
          data-tooltip-delay-show={750}
        >
          {differenceInSeconds(currentTimestamp ?? data.end, data.start)} /{" "}
          {differenceInSeconds(data.end, data.start)}
        </span>
        <Timeline
          value={currentTimestamp ?? data.end}
          start={data.start} available={maxTimestamp} end={data.end}
          onChange={onTimelineChange}
          interval={search.playbackInterval}
          onIntervalChange={(newInterval: number) => {
            updateSearchParams({playbackInterval: newInterval})
          }}
          onRateChange={(newRate: number) => {
            setRate(newRate);
          }}
          rate={rate}
        />
        <Tooltip id="play-button" />
        <Tooltip id="restart-button" />
        <Tooltip id="current-timestamp" />
      </div>
    </div>
  );
}
