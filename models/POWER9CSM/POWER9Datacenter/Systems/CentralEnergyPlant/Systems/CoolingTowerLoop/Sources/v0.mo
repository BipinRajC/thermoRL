within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.Sources;
model v0
  extends BaseClasses.PartialSources(redeclare replaceable Data.NULL data);
  input SI.Temperature T_ext=20+273.15 "Wet bulb temperature"
    annotation (Dialog(group="Inputs"));

  Modelica.Blocks.Routing.Replicator replicator3(nout=16)
    annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-60,-10})));
  TRANSFORM.Blocks.ArrayToMatrix arrayToMatrix2(
    n=16,
    nrows=4,
    ncolumns=4)
    annotation (Placement(transformation(extent={{-40,-20},{-20,0}})));
  Modelica.Blocks.Sources.RealExpression T_ext_int(y=T_ext)
    annotation (Placement(transformation(extent={{-100,-20},{-80,0}})));
equation
  connect(replicator3.y,arrayToMatrix2. u)
    annotation (Line(points={{-49,-10},{-42,-10}},
                                                 color={0,0,127}));
  connect(controlBus.T_ext_coolingTower, arrayToMatrix2.y) annotation (Line(
      points={{0,-100},{0,-10},{-19,-10}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(T_ext_int.y, replicator3.u)
    annotation (Line(points={{-79,-10},{-72,-10}}, color={0,0,127}));
end v0;
