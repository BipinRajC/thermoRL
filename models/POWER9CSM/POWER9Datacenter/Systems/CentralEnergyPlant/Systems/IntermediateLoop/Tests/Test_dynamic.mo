within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.IntermediateLoop.Tests;
model Test_dynamic
  extends Test_steady(
    boundary_inlet_1(                     use_T_in=false),
    boundary_inlet_2(use_p_in=true,      use_T_in=true),
    boundary_outlet_1(use_p_in=false, use_T_in=false),
    boundary_outlet_2(use_p_in=false, use_T_in=false));
  Modelica.Blocks.Sources.Sine sine_T_2(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a2_nominal.T,
    startTime=650) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={110,-50})));
  Modelica.Blocks.Sources.Sine sine_p_2(
    amplitude=0.05*simulator[1].port_a2_nominal.p,
    f=1/100,
    offset=simulator[1].port_a2_nominal.p,
    startTime=400) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={110,-20})));
equation
  connect(sine_T_2.y, boundary_inlet_2.T_in) annotation (Line(points={{99,-50},
          {90,-50},{90,-36},{82,-36}}, color={0,0,127}));
  connect(sine_p_2.y, boundary_inlet_2.p_in) annotation (Line(points={{99,-20},
          {90,-20},{90,-32},{82,-32}}, color={0,0,127}));
  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Dassl"));
end Test_dynamic;
