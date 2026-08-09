import { BaseSyntheticEvent } from "react";
import { ColumnHeader } from "../../../../models/dataGrid/columnHeader.model";

export function ColumnSelection({
  columns,
  openIndex,
  onClick,
}: {
  columns: ColumnHeader[];
  openIndex: number;
  onClick: (e: BaseSyntheticEvent, index: number) => void;
}) {
  return (
    <div className="flex w-1/4 flex-col border-r-2">
      {[...columns.entries()]
        .filter(([_index, column]) => column.filterable ?? true)
        .map(([index, column]) => (
          <button
            key={column.propertyName}
            className={`flex items-center justify-between border-b-2 px-4 py-2 font-medium transition-opacity duration-500 hover:opacity-50 focus:outline-none ${index === openIndex && "bg-blue-500 text-white hover:opacity-100"}`}
            onClick={(e) => onClick(e, index)}
          >
            <span>{column.name}</span>
            {index !== openIndex &&
              column.activeFilters.some((filter) => filter.value) && (
                <div className="h-2 w-2 rounded-full bg-blue-500" />
              )}
          </button>
        ))
      }
    </div>
  );
}
