import { keepPreviousData, queryOptions, infiniteQueryOptions } from "@tanstack/react-query";
import axios from "axios";
import { Simulation } from "../models/Simulation.model";
import { CoolingCDU } from "../models/CoolingCDU.model";
import { CoolingCEP } from "../models/CoolingCEP.model";
import { Job } from "../models/Job.model";
import { groupBy, sortBy } from "lodash";
import { SimulationStatistic } from "../models/SimulationStatistic.model";
import { SystemInfo } from "../models/SystemInfo.model";

export interface ListResponse<T> {
  total_results: number;
  offset: number;
  limit: number;
  results: T[];
}

export interface TimeSeriesPoint {
  timestamp: string;
}
export interface TimeSeriesResponse<T extends TimeSeriesPoint = TimeSeriesPoint> {
  granularity: number;
  start: string;
  end: string;
  data: T[];
}

export interface TimeSeriesParams {
  start?: string;
  end?: string;
  granularity?: number;
  resolution?: number;
}

export const simulationConfigurationQueryOptions = (simulationId: string) =>
  queryOptions({
    queryKey: ["simulation", "configuration", simulationId],
    queryFn: async (): Promise<Simulation> => {
      const res = await axios.get(`/simulation/${simulationId}`);
      return res.data;
    },
    refetchOnWindowFocus: false,
    refetchInterval: (query) => query.state.data?.execution_end ? false : 3000,
    staleTime: (query) => query.state.data?.execution_end ? Infinity : 1000,
  });

/**
 * Query jobs from the job endpoint.
 * sort should be passed as a list like ["desc:state", "asc:sim_id"]
 * filters is in the format ["state=eq:RUNNING"]
 * This should be passed to useInfiniteQuery
 * TODO: allow passing sort/filters in cleaner format than raw query params.
 */
export const simulationList = (
  params?: {
    limit?: number,
    fields?: string[], sort?: string[],
    filters?: string[],
  }
) => {
  let searchParams: string[] = []
  // axios adds `[]` to array params so we'll serialize it manually instead
  searchParams.push(...(params?.sort?.map(s => `sort=${s}`) ?? []));
  // Just specify filters as an array of ["job_id=eq:1"] for now
  searchParams.push(...(params?.filters ?? []));
  const limit = params?.limit ?? 100;

  return infiniteQueryOptions({
    queryKey: ["simulation", "list", params],
    queryFn: async ({ pageParam }) => {
      const res = await axios.get<ListResponse<Simulation>>(
        `/simulation/list?${searchParams.join("&")}`, {
        params: {
          limit: limit, offset: pageParam,
          fields: params?.fields?.join(","),
        },
      });
      return res.data;
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages, lastPageParam, _allPageParams) =>
      (lastPageParam + limit < lastPage.total_results) ? lastPageParam + limit : undefined,
  })
}

export const simulationCoolingCDUQueryOptions = (
  simulationId: string,
  params?: TimeSeriesParams,
) =>
  queryOptions({
    queryKey: ["simulation", "cooling", "cdu", simulationId, params],
    queryFn: async () => {
      const res = await axios.get<
        TimeSeriesResponse<CoolingCDU>
      >(`/simulation/${simulationId}/cooling/cdu`, { params: params });
      return res.data;
    },
    select: (data) => {
      let groupedTimeData =
        Object.entries(groupBy(data.data, "timestamp"))
          .map(([k, v]) => ({timestamp: k, cdus: v}));
      groupedTimeData = sortBy(groupedTimeData, "timestamp")
      return { ...data, data: groupedTimeData };
    },
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

export const simulationCoolingCEPQueryOptions = (
  simulationId: string,
  params: TimeSeriesParams = {},
) => queryOptions({
    queryKey: ["simulation", "cooling", "cep", simulationId, params],
    queryFn: async () => {
      const res = await axios.get<
        TimeSeriesResponse<CoolingCEP>
      >(`/simulation/${simulationId}/cooling/cep`, { params: params });
      return res.data;
    },
  });

export const simulationSystemStatsQueryOptions = (
  simulationId: string,
  params: TimeSeriesParams = {},
) => queryOptions({
    queryKey: ["simulation", "system", "statistics", simulationId, params],
    queryFn: async () => {
      const res = await axios.get<
        TimeSeriesResponse<SimulationStatistic>
      >(`/simulation/${simulationId}/scheduler/system`, { params: params });
      return res.data;
    },
  });

/**
 * Query jobs from the job endpoint.
 * sort should be passed as a list like ["desc:name", "asc:job_id"]
 * filters is in the format ["job_id=eq:5"]
 * This should be passed to useInfiniteQuery
 * TODO: allow passing sort/filters in cleaner format than raw query params.
 */
export const simulationSchedulerJobs = (
  simulationId: string,
  params?: {
    start?: string, end?: string,
    limit?: number,
    fields?: string[], sort?: string[],
    filters?: string[],
  }
) => {
  let searchParams: string[] = []
  // axios adds `[]` to array params so we'll serialize it manually instead
  searchParams.push(...(params?.sort?.map(s => `sort=${s}`) ?? []));
  // Just specify filters as an array of ["job_id=eq:1"] for now
  searchParams.push(...(params?.filters ?? []));
  const limit = params?.limit ?? 1000;

  return infiniteQueryOptions({
    queryKey: ["simulation", "scheduler", "jobs", simulationId, params],
    queryFn: async ({ pageParam }) => {
      const res = await axios.get<ListResponse<Job>>(
        `/simulation/${simulationId}/scheduler/jobs?${searchParams.join("&")}`, {
        params: {
          start: params?.start, end: params?.end,
          limit: limit, offset: pageParam,
          fields: params?.fields?.join(","),
        },
      });
      return res.data;
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages, lastPageParam, _allPageParams) =>
      (lastPageParam + limit < lastPage.total_results) ? lastPageParam + limit : undefined,
  })
}

export const getSystemInformation = (system: string) =>
  queryOptions({
    queryKey: ["system", system],
    queryFn: async () => {
      const res = await axios.get<SystemInfo>(`/system/${system}`);
      return res.data;
    },
    staleTime: Infinity,
  });

export const getSystems = () =>
  queryOptions({
    queryKey: ["system", "list"],
    queryFn: async () => {
      const res = await axios.get<SystemInfo[]>(`/system/list`);
      return res.data;
    },
    staleTime: Infinity,
  });
