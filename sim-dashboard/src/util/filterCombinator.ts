import { ColumnHeader } from "../models/dataGrid/columnHeader.model";

export function sortCombinator(columns: ColumnHeader[]) {
  return columns
    .flatMap(col => col.sort.direction ? [`${col.sort.direction}:${col.propertyName}`] : [])
}

export function operatorCombinator(columns: ColumnHeader[]) {
  return columns
    .flatMap(col => col.activeFilters.map(f => `${col.propertyName}=${f.operator}:${f.value}`))
}
