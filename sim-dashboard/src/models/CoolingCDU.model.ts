export interface CoolingCDU {
  timestamp: string;
  name: string;
  row: number;
  col: number;
  rack_1_power: number;
  rack_2_power: number;
  rack_3_power: number;
  total_power: number;
  rack_1_loss: number;
  rack_2_loss: number;
  rack_3_loss: number;
  total_loss: number;

  work_done_by_cdup?: number;
  rack_return_temp?: number;
  rack_supply_temp?: number;
  rack_supply_pressure?: number;
  rack_return_pressure?: number;
  rack_flowrate?: number;
  facility_return_temp?: number;
  facility_supply_temp?: number;
  facility_supply_pressure?: number;
  facility_return_pressure?: number;
  facility_flowrate?: number;
}
