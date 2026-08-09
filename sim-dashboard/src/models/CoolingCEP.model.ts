export interface CoolingCEP {
  timestamp: string;
  htw_flowrate: number;
  ctw_flowrate: number;
  htw_return_pressure: number;
  htw_supply_pressure: number;
  ctw_return_pressure: number;
  ctw_supply_pressure: number;
  htw_return_temp: number;
  htw_supply_temp: number;
  ctw_return_temp: number;
  ctw_supply_temp: number;
  power_consumption_htwps: number;
  power_consumption_ctwps: number;
  power_consumption_fan: number;
  htwp_speed: number;
  nctwps_staged: number;
  nhtwps_staged: number;
  pue_output: number;
  nehxs_staged: number;
  ncts_staged: number;
  facility_return_temp: number;
  cdu_loop_bypass_flowrate: number;
}
