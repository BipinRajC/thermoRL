within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.IntermediateLoop.Controls;
model CS_Constant
  extends BaseClasses.PartialControls(redeclare replaceable Data.NULL data);

  Modelica.Blocks.Sources.Constant opening_valve(k=0.5)
    annotation (Placement(transformation(extent={{-30,20},{-10,40}})));

  Modelica.Blocks.Routing.Replicator replicator(nout=4)
    annotation (Placement(transformation(extent={{10,20},{30,40}})));
  Modelica.Blocks.Sources.Constant opening_valve_heatExchanger_hot(k=0.6)
    annotation (Placement(transformation(extent={{-30,-10},{-10,10}})));
  Modelica.Blocks.Routing.Replicator replicator1(nout=4)
    annotation (Placement(transformation(extent={{10,-10},{30,10}})));
  Modelica.Blocks.Routing.Replicator replicator2(nout=4)
    annotation (Placement(transformation(extent={{10,-40},{30,-20}})));
  Modelica.Blocks.Sources.Constant opening_valve_heatExchanger_cold(k=0.4)
    annotation (Placement(transformation(extent={{-30,-40},{-10,-20}})));
  Modelica.Blocks.Sources.Constant Nrel_pump(k=1)
    annotation (Placement(transformation(extent={{-30,50},{-10,70}})));
  Modelica.Blocks.Routing.Replicator replicator3(nout=4)
    annotation (Placement(transformation(extent={{10,50},{30,70}})));
equation

  connect(opening_valve.y, replicator.u)
    annotation (Line(points={{-9,30},{8,30}},  color={0,0,127}));
  connect(opening_valve_heatExchanger_hot.y, replicator1.u)
    annotation (Line(points={{-9,0},{8,0}},  color={0,0,127}));
  connect(opening_valve_heatExchanger_cold.y, replicator2.u)
    annotation (Line(points={{-9,-30},{8,-30}},  color={0,0,127}));
  connect(controlBus.opening_valve_heatExchanger_hot, replicator1.y)
    annotation (Line(
      points={{0,-100},{180,-100},{180,0},{31,0}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.opening_valve_heatExchanger_cold, replicator2.y)
    annotation (Line(
      points={{0,-100},{180,-100},{180,-30},{31,-30}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(Nrel_pump.y, replicator3.u)
    annotation (Line(points={{-9,60},{8,60}},  color={0,0,127}));
  connect(controlBus.opening_pumpTrain, replicator.y) annotation (Line(
      points={{0,-100},{180,-100},{180,30},{31,30}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.N_pumpTrain, replicator3.y) annotation (Line(
      points={{0,-100},{132,-100},{132,-98},{180,-98},{180,60},{31,60}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
end CS_Constant;
