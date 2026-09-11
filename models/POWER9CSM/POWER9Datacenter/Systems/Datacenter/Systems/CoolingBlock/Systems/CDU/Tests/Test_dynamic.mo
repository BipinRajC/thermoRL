within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Tests;
model Test_dynamic
  extends Test_steady(
    boundary_inlet_1(use_p_in=true, use_T_in=true),
    boundary_outlet_1(use_p_in=false, use_T_in=false),
    boundary_inlet_2(use_p_in=true, use_T_in=true));
  Modelica.Blocks.Sources.Sine sine_T(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a1_nominal.T,
    startTime=500) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,30})));
  Modelica.Blocks.Sources.Sine sine_p(
    amplitude=0.25*simulator[1].port_a1_nominal.p,
    f=1/100,
    offset=simulator[1].port_a1_nominal.p,
    startTime=250) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-110,60})));
  Modelica.Blocks.Sources.Sine sine_T_2(
    amplitude=5,
    f=1/100,
    offset=simulator[1].port_a2_nominal.T,
    startTime=600) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={110,-50})));
  Modelica.Blocks.Sources.Sine sine_p_2(
    amplitude=0.25*simulator[1].port_a2_nominal.p,
    f=1/100,
    offset=simulator[1].port_a2_nominal.p,
    startTime=400) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={110,-20})));
equation
  connect(sine_T.y, boundary_inlet_1.T_in) annotation (Line(points={{-99,30},{
          -90,30},{-90,44},{-82,44}}, color={0,0,127}));
  connect(boundary_inlet_1.p_in, sine_p.y) annotation (Line(points={{-82,48},{
          -90,48},{-90,60},{-99,60}}, color={0,0,127}));
  connect(boundary_inlet_2.p_in, sine_p_2.y) annotation (Line(points={{82,-32},
          {90,-32},{90,-20},{99,-20}}, color={0,0,127}));
  connect(sine_T_2.y, boundary_inlet_2.T_in) annotation (Line(points={{99,-50},
          {90,-50},{90,-36},{82,-36}}, color={0,0,127}));
  annotation (Diagram(coordinateSystem(extent={{-140,-100},{140,
            100}})), experiment(
      StopTime=2500,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Dassl"));
end Test_dynamic;
