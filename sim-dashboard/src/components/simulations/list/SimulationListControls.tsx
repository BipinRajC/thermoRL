import { Link } from "@tanstack/react-router";
import { SimulationsDataGridFilter } from "./SimulationsDataGridFilters";
import { ColumnHeader } from "../../../models/dataGrid/columnHeader.model";
import { SimulationsDataGridHistogram } from "./SimulationsDataGridHistogram";

export function SimulationListControls({
  columns,
  setColumns,
  totalRows,
}: {
  columns: ColumnHeader[];
  setColumns: (columns: ColumnHeader[]) => void;
  totalRows: number;
}) {
  return (
    <div className="h-16 flex">
      <SimulationsDataGridHistogram />
      <div className="flex flex-col">
        <span className="border-b-2 px-3 py-1 border-l-2 dark:text-neutral-200 border-neutral-400 dark:border-neutral-700">
          {totalRows} Simulation(s)
        </span>
        <SimulationsDataGridFilter columns={columns} setColumns={setColumns} />
      </div>
      <Link
        to="/simulations/new"
        className="bg-green-600 text-white px-3 text-center flex items-center transition-opacity duration-500 hover:opacity-80"
      >
        New Simulation
      </Link>
    </div>
  );
}
