// direction will be undefined if the column isn't currently being sorted
export type SortDirection = "asc"|"desc"|null;
export type SortDetails = { sortable: boolean, direction: "asc"|"desc"|SortDirection };
