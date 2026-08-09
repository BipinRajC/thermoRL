import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { SimulationListControls } from "../components/simulations/list/SimulationListControls";
import { SimulationsDataGrid } from "../components/simulations/list/SimulationsDataGrid";
import { columns as SimulationColumns } from "../components/simulations/list/SimulationsGridColumns";
import { useInfiniteQuery } from "@tanstack/react-query";
import { operatorCombinator, sortCombinator } from "../util/filterCombinator";
import { SortDirection } from "../models/filters/sortDetails.model";
import { cloneDeep } from "lodash";
import { simulationList } from "../util/queryOptions";

export const Route = createFileRoute("/simulations/")({
  component: SimulationList,
});


function SimulationList() {
  const [columns, setColumns] = useState(structuredClone(SimulationColumns));

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    ...simulationList({
      limit: 18,
      fields: ["all"],
      sort: sortCombinator(columns),
      filters: operatorCombinator(columns),
    })
  });
  const simulations = data?.pages.map((page) => page.results).flat() ?? [];

  const onSort = (columnName: string, direction: SortDirection) => {
    const updatedColumns = cloneDeep(columns);
    const currentColumn = updatedColumns.find(
      (column) => column.name === columnName,
    );

    if (currentColumn) {
      currentColumn.sort.direction = direction;
    }

    setColumns(updatedColumns);
  };

  return (
    <div className="flex flex-1 flex-col">
      <SimulationListControls
        columns={columns}
        setColumns={setColumns}
        totalRows={data?.pages[0].total_results ?? 0}
      />
      <SimulationsDataGrid
        isLoading={isLoading}
        isError={isError}
        columns={columns}
        onSort={onSort}
        rows={simulations}
        fetchNextPage={fetchNextPage}
        isFetchingNextPage={isFetchingNextPage}
        hasNextPage={hasNextPage}
        total_results={data?.pages[0].total_results ?? 0}
      />
    </div>
  );
}
