import { PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { FilterOperators } from "../../../../models/filters/filterOperators.enum";
import { Select } from "../../dropdown";
import { ColumnSelection } from "./ColumnSelection";
import { FilterInput } from "./FilterInput";
import { Tooltip } from "react-tooltip";
import { Button } from "../../button";
import { ColumnHeader } from "../../../../models/dataGrid/columnHeader.model";
import {
  onAddColumn,
  onApplyFilters,
  onClearFilters,
  onClose,
  onColumnChange,
  onColumnSelection,
  onDeleteColumn,
} from "../../../../util/hooks/useListFilter";

export function FilterSection({
  columns,
  openColumn,
  currentColumn,
  onColumnSelection,
  onClose,
  onColumnChange,
  onAddColumn,
  onDeleteColumn,
  onApplyFilters,
  onClearFilters,
}: {
  columns: ColumnHeader[];
  openColumn: number;
  currentColumn: ColumnHeader;
  onColumnSelection: onColumnSelection;
  onClose: onClose;
  onAddColumn: onAddColumn;
  onColumnChange: onColumnChange;
  onDeleteColumn: onDeleteColumn;
  onApplyFilters: onApplyFilters;
  onClearFilters: onClearFilters;
}) {
  return (
    <>
      <section className="flex flex-1 overflow-auto">
        <ColumnSelection
          columns={columns}
          openIndex={openColumn}
          onClick={onColumnSelection}
        />
        <div className="flex flex-1 flex-col gap-4 overflow-auto px-8 py-4">
          {currentColumn?.activeFilters.map((filter, index) => (
            <div
              key={`${openColumn}-filter-${index}`}
              className="flex items-center gap-4"
            >
              <Select
                choices={currentColumn.operators.map((operator) => ({
                  label:
                    Object.keys(FilterOperators)[
                      Object.values(FilterOperators).indexOf(operator)
                    ],
                  value: operator,
                }))}
                value={filter.operator}
                onChange={(e) =>
                  onColumnChange({
                    index: index,
                    operator: e.target.value as FilterOperators,
                    value: filter.value,
                  })
                }
              />
              <div className="flex-1">
                <FilterInput
                  fieldType={currentColumn.inputType}
                  value={filter.value}
                  onChange={(value: string | null) =>
                    onColumnChange({
                      index: index,
                      operator: filter.operator,
                      value: value,
                    })
                  }
                  choices={
                    currentColumn.inputType === "select"
                      ? currentColumn.selectOptions
                      : []
                  }
                />
              </div>
              <button
                className="ml-auto transition-opacity duration-500 hover:opacity-75"
                onClick={(e) => onDeleteColumn(e, index)}
                data-tooltip-id="delete-filter-tooltip"
                data-tooltip-content={"Delete Filter"}
                data-tooltip-delay-show={500}
              >
                <TrashIcon className="h-5 w-5 text-red-600" />
              </button>
              <Tooltip id="delete-filter-tooltip" />
            </div>
          ))}
          <button className="flex items-center gap-2" onClick={onAddColumn}>
            <PlusIcon className="h-4 w-4 text-green-500" />
            <span>Add New Filter</span>
          </button>
        </div>
      </section>
      <footer className="flex items-center justify-between border-t-2 px-4 py-2">
        <Button
          type="button"
          variant="outlined"
          dense
          onClick={(e) => {
            e.preventDefault();
            onClearFilters();
          }}
        >
          Clear Filters
        </Button>
        <div className="flex items-center justify-end gap-4">
          <Button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              onClose(true);
            }}
            variant="outlined"
            dense
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              onApplyFilters();
            }}
            variant="filled"
            dense
          >
            Apply Filters
          </Button>
        </div>
      </footer>
    </>
  );
}
