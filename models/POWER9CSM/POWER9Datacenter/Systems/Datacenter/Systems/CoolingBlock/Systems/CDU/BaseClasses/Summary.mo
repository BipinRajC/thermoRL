within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.BaseClasses;
model Summary
  extends TemplatesCSM.BaseClasses.Systems.PartialSummary;

  input SI.MassFlowRate m_flow_prim = 0.0 "CDU primary mass flow rate" annotation(Dialog(group="Inputs"));
  output Real V_flow_prim_GPM = m_flow_prim/0.063 "CDU primary volume flow rate in GPM"  annotation(Dialog(group="Outputs", enable=false));

  input SI.MassFlowRate m_flow_sec = 0.0 "CDU secondary mass flow rate" annotation(Dialog(group="Inputs"));
  output Real V_flow_sec_GPM = m_flow_sec/0.063 "CDU secondary volume flow rate in GPM"  annotation(Dialog(group="Outputs", enable=false));

  input SI.HeatFlowRate W_flow_CDUP = 0.0 "CDU pump power consumption" annotation(Dialog(group="Inputs"));
  output Real W_flow_CDUP_kW = W_flow_CDUP*1e-3 "CDU pump power consumption in kW"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Temperature T_prim_s = 0.0 "CDU primary supply temperature" annotation(Dialog(group="Inputs"));
  output Real T_prim_s_C = T_prim_s-273.15 "CDU primary supply temperature in C"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Temperature T_prim_r = 0.0 "CDU primary return temperature" annotation(Dialog(group="Inputs"));
  output Real T_prim_r_C = T_prim_r-273.15 "CDU primary return temperature in C"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Temperature T_sec_s = 0.0 "CDU secondary supply temperature" annotation(Dialog(group="Inputs"));
  output Real T_sec_s_C = T_sec_s-273.15 "CDU secondary supply temperature in C"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Temperature T_sec_r = 0.0 "CDU secondary return temperature" annotation(Dialog(group="Inputs"));
  output Real T_sec_r_C = T_sec_r-273.15 "CDU secondary return temperature in C"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Pressure p_prim_s = 0.0 "CDU primary supply pressure" annotation(Dialog(group="Inputs"));
  output Real p_prim_s_psig = p_prim_s*1e-5*14.503773773 - 14.503773773 "CDU primary supply pressure in psig"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Pressure p_prim_r = 0.0 "CDU primary return pressure" annotation(Dialog(group="Inputs"));
  output Real p_prim_r_psig = p_prim_r*1e-5*14.503773773 - 14.503773773 "CDU primary return pressure in psig"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Pressure p_sec_s = 0.0 "CDU secondary supply pressure" annotation(Dialog(group="Inputs"));
  output Real p_sec_s_psig = p_sec_s*1e-5*14.503773773 - 14.503773773 "CDU secondary supply pressure in psig"  annotation(Dialog(group="Outputs", enable=false));

  input SI.Pressure p_sec_r = 0.0 "CDU secondary return pressure" annotation(Dialog(group="Inputs"));
  output Real p_sec_r_psig = p_sec_r*1e-5*14.503773773 - 14.503773773 "CDU secondary return pressure in psig"  annotation(Dialog(group="Outputs", enable=false));

end Summary;
