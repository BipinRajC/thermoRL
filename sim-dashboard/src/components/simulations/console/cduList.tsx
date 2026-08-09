import { CoolingCDU } from "../../../models/CoolingCDU.model";
import { ConsoleHeader } from "../../shared/simulation/consoleHeader";

const columns = [
  "CDU",
  "Rack 1 (kW)",
  "Rack 2 (kW)",
  "Rack 3 (kW)",
  "Sum (kW)",
  "Loss (kW)",
  "Facility Supply Temperature (°C)",
  "Facility Return Temperature (°C)",
  "Rack Supply Temperature (°C)",
  "Rack Return Temperature (°C)",
];

export function CDUList({ metrics = []}: { metrics?: CoolingCDU[] }) {
  return (
    <div className="col-start-1 col-end-8 row-start-4">
      <ConsoleHeader>Power and Temperature</ConsoleHeader>
      <div className="border-2 border-neutral-400 text-sm dark:border-neutral-900">
        <div className="grid grid-cols-10 border-b-2 border-neutral-400 bg-neutral-300 text-xs dark:border-neutral-900 dark:bg-neutral-700 dark:text-neutral-200">
          {columns.map((col, index) => (
            <div
              className={`flex items-end justify-center ${index === columns.length - 1 ? "" : "border-r-2"} border-neutral-400 px-2 dark:border-neutral-900`}
              key={col}
            >
              <span
                className="overflow-hidden text-ellipsis text-center"
                title={col}
              >
                {col}
              </span>
            </div>
          ))}
        </div>
        {metrics.map((cdu, index) => (
          <div
            className="grid grid-cols-10 text-center"
            key={cdu.name}
          >
            <div className="border-r-2 border-neutral-400 text-cyan-500 dark:border-neutral-900">
              {index + 1}
            </div>
            <div className="border-r-2 border-neutral-400 text-green-600 dark:border-neutral-900 dark:text-green-500">
              {cdu.rack_1_power?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-green-600 dark:border-neutral-900 dark:text-green-500">
              {cdu.rack_2_power?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-green-600 dark:border-neutral-900 dark:text-green-500">
              {cdu.rack_3_power?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-green-600 dark:border-neutral-900 dark:text-green-500">
              {cdu.total_power?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-green-600 dark:border-neutral-900 dark:text-green-500">
              {cdu.total_loss?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-blue-500 dark:border-neutral-900">
              {cdu.facility_supply_temp?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-red-500 dark:border-neutral-900">
              {cdu.facility_return_temp?.toFixed(1)}
            </div>
            <div className="border-r-2 border-neutral-400 text-blue-500 dark:border-neutral-900">
              {cdu.rack_supply_temp?.toFixed(1)}
            </div>
            <div className=" text-red-500">
              {cdu.rack_return_temp?.toFixed(1)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
