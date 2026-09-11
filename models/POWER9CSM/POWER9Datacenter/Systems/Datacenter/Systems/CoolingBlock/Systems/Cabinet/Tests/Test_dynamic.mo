within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.Cabinet.Tests;
model Test_dynamic
  extends Test_steady(boundary_inlet(use_m_flow_in=true, use_T_in=true));
  Modelica.Blocks.Sources.Sine sine_m_flow(
    amplitude=0.25*simulator[1].port_a_start.m_flow,
    f=1/100,
    offset=simulator[1].port_a_start.m_flow,
    startTime=250)
    annotation (Placement(transformation(extent={{-120,10},{-100,30}})));
  Modelica.Blocks.Sources.Sine sine_T(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a_start.T,
    startTime=500)
    annotation (Placement(transformation(extent={{-120,-20},{-100,0}})));
  Modelica.Blocks.Sources.CombiTimeTable combiTimeTable
    annotation (Placement(transformation(extent={{-208,34},{-188,54}})));
equation
  connect(sine_T.y, boundary_inlet.T_in) annotation (Line(points={{-99,-10},{-90,
          -10},{-90,4},{-82,4}}, color={0,0,127}));
  connect(boundary_inlet.m_flow_in, sine_m_flow.y) annotation (Line(points={{-80,
          8},{-90,8},{-90,20},{-99,20}}, color={0,0,127}));
end Test_dynamic;
