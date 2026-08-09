import { CoolingCDU } from "../../../models/CoolingCDU.model";
import { ConsoleHeader } from "../../shared/simulation/consoleHeader";
import { sumBy } from "lodash"

const statistics = [
  {
    name: "Work Done by CDUPs (kW)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.work_done_by_cdup ?? 0) / metrics.length
  },
  {
    name: "Facility Supply Pressure (psig)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.facility_supply_pressure ?? 0) / metrics.length,
  },
  {
    name: "Facility Return Pressure (psig)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.facility_return_pressure ?? 0) / metrics.length,
  },
  {
    name: "Facility Flowrate (gpm)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.facility_flowrate ?? 0) / metrics.length,
  },
  {
    name: "Rack Supply Pressure (psig)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.rack_supply_pressure ?? 0) / metrics.length,
  },
  {
    name: "Rack Return Pressure (psig)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.rack_return_pressure ?? 0) / metrics.length,
  },
  {
    name: "Rack Flowrate (gpm)",
    value: (metrics: CoolingCDU[]) =>
      sumBy(metrics, d => d.rack_flowrate ?? 0) / metrics.length,
  },
];

export function PressureFlowRate({ metrics = [] }: { metrics?: CoolingCDU[] }) {
  return (
    <div className="col-start-1 col-end-8 row-start-2 row-end-4">
      <ConsoleHeader>Pressure and Flow Rates</ConsoleHeader>
      <div className="border-2 border-neutral-400 dark:border-neutral-900">
        <div className="flex w-full border-b-2 border-neutral-400 bg-neutral-300 text-xs dark:border-neutral-900 dark:bg-neutral-700">
          <span className="flex-1 px-2 dark:text-neutral-200">Output</span>
          <div className="w-[2px] bg-neutral-400 dark:bg-neutral-900" />
          <span className="flex-1 text-center dark:text-neutral-200">
            Average Value
          </span>
        </div>
        <div className="flex flex-col">
          {statistics.map((stat) => (
            <div className="flex text-sm dark:text-neutral-200" key={stat.name}>
              <span className="flex-1 px-2">{stat.name}</span>
              <div className="w-[2px] bg-neutral-400 dark:bg-neutral-900" />
              <span className="flex-1 text-center">
                {stat.value(metrics).toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
