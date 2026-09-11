within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.Controls;
model CS_Constant "CS for CTWP pump, CT staging and CTWP staging"
  extends BaseClasses.PartialControls(redeclare replaceable Data.NULL data);

  Modelica.Blocks.Sources.Constant opening_valve(k=0.5) annotation (Placement(
        transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-60,-40})));

  Modelica.Blocks.Routing.Replicator replicator(nout=4)
    annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-20,-40})));
  Modelica.Blocks.Sources.Constant Nrel_CTWP(k=1) annotation (Placement(
        transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-60,-10})));
  Modelica.Blocks.Routing.Replicator replicator1(nout=4)
    annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-20,-10})));
  Modelica.Blocks.Sources.Constant opening_coolingTower(k=1) annotation (
      Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-80,40})));
  Modelica.Blocks.Routing.Replicator replicator2(nout=16)
    annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-50,40})));
  TRANSFORM.Blocks.ArrayToMatrix arrayToMatrix1(
    n=16,
    nrows=4,
    ncolumns=4)
    annotation (Placement(transformation(extent={{-30,30},{-10,50}})));
equation

  connect(opening_valve.y, replicator.u)
    annotation (Line(points={{-49,-40},{-32,-40}}, color={0,0,127}));
  connect(Nrel_CTWP.y, replicator1.u)
    annotation (Line(points={{-49,-10},{-32,-10}},
                                                 color={0,0,127}));
  connect(opening_coolingTower.y, replicator2.u)
    annotation (Line(points={{-69,40},{-62,40}}, color={0,0,127}));
  connect(replicator2.y, arrayToMatrix1.u)
    annotation (Line(points={{-39,40},{-32,40}}, color={0,0,127}));
  connect(controlBus.opening_pumpTrain, replicator.y) annotation (Line(
      points={{0,-100},{0,-40},{-9,-40}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.N_pumpTrain, replicator1.y) annotation (Line(
      points={{0,-100},{0,-10},{-9,-10}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.opening_coolingTower, arrayToMatrix1.y) annotation (Line(
      points={{0,-100},{0,40},{-9,40}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
end CS_Constant;
