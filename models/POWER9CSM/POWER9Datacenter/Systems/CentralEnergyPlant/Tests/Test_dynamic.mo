within POWER9Datacenter.Systems.CentralEnergyPlant.Tests;
model Test_dynamic
  extends Test_steady(
    boundary_inlet(use_p_in=true,      use_T_in=true),
    boundary_outlet(use_p_in=true, use_T_in=false));
  Modelica.Blocks.Sources.Sine sine_T(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a_nominal.T,
    startTime=650) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,-10})));
  Modelica.Blocks.Sources.Sine sine_p(
    amplitude=0.25*simulator[1].port_a_nominal.p,
    f=1/100,
    offset=simulator[1].port_a_nominal.p,
    startTime=400) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,20})));
  Modelica.Blocks.Sources.Sine sine_p_2(
    amplitude=0.25*simulator[1].port_b_nominal.p,
    f=1/100,
    offset=simulator[1].port_b_nominal.p,
    startTime=400) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={110,20})));
equation
  connect(sine_T.y, boundary_inlet.T_in) annotation (Line(points={{-99,-10},{
          -90,-10},{-90,4},{-82,4}}, color={0,0,127}));
  connect(sine_p.y, boundary_inlet.p_in) annotation (Line(points={{-99,20},{-90,
          20},{-90,8},{-82,8}}, color={0,0,127}));
  connect(sine_p_2.y, boundary_outlet.p_in)
    annotation (Line(points={{99,20},{90,20},{90,8},{82,8}}, color={0,0,127}));
end Test_dynamic;
