within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Tests;
model Test_dynamic
  extends Test_steady   (
    boundary_inlet(use_m_flow_in=true, use_T_in=true),
    boundary_outlet(use_p_in=false, use_T_in=false));
  Modelica.Blocks.Sources.Sine sine_T(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a_nominal.T,
    startTime=500) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,-10})));
  Modelica.Blocks.Sources.Sine sine_m_flow(
    amplitude=0.25*simulator[1].port_a_nominal.m_flow,
    f=1/100,
    offset=simulator[1].port_a_nominal.m_flow,
    startTime=250) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,20})));
equation
  connect(sine_m_flow.y, boundary_inlet.m_flow_in) annotation (Line(points={{-99,
          20},{-90,20},{-90,8},{-80,8}}, color={0,0,127}));
  connect(sine_T.y, boundary_inlet.T_in) annotation (Line(points={{-99,-10},{-90,
          -10},{-90,4},{-82,4}}, color={0,0,127}));
end Test_dynamic;
