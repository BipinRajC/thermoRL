import { useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { BaseSyntheticEvent, useCallback, useState } from "react";
import { Route as SimulationCoolingRoute } from "../../routes/simulations.$simulationId.cooling";
import { debounce } from "lodash";
import { Input } from "../shared/input";

export function TimeStepBar() {
  const navigate = useNavigate();
  const { resolution, granularity } = useSearch({
    from: SimulationCoolingRoute.fullPath,
  });
  const { simulationId } = useParams({ from: SimulationCoolingRoute.fullPath });
  const [timestepValue, setTimestepValue] = useState({
    resolution,
    granularity,
  });

  const onChange = ({ g, r }: { g?: number; r?: number }) => {
    setTimestepValue({ granularity: g, resolution: r });

    debouncedNavigate({ g, r });
  };

  const debouncedNavigate = useCallback(
    debounce(({ g, r }: { g?: number; r?: number }) => {
      navigate({
        from: SimulationCoolingRoute.fullPath,
        params: { simulationId },
        search: (prev) => ({
          ...prev,
          granularity: g,
          resolution: r,
        }),
      });
    }, 500),
    [],
  );

  return (
    <div className="my-4 flex items-center px-6">
      <span className="mr-2 dark:text-neutral-200">
        Timestep Type: Granularity (s)
      </span>
      <div className="ml-4">
        <Input
          label="Granularity:"
          labelAlignment="horizontal"
          value={timestepValue.granularity}
          onChange={(e: BaseSyntheticEvent) => {
            const value = e.target.value;
            if (!value || Number(value) > 0) {
              onChange({ g: value, r: undefined });
            }
          }}
        />
      </div>
    </div>
  );
}
