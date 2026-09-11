within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.Cabinet.Sources;
model v0
  extends BaseClasses.PartialSources(redeclare replaceable
      Data.NULL data);
  input SI.HeatFlowRate Q_flow_total=0.0
    "Total heat flow to the cabinet"
    annotation (Dialog(group="Input"));

  input SI.Temperature T_Air=273.15+24.05
    "Room Air Temperature"
    annotation (Dialog(group="Input"));
  Modelica.Blocks.Sources.RealExpression Q_flow_int(y=
        Q_flow_total) annotation (Placement(transformation(
          extent={{-40,-70},{-20,-50}})));
  Modelica.Blocks.Sources.RealExpression Air_Temperature(y=T_Air) annotation (
      Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=180,
        origin={30,-60})));
equation

  connect(controlBus.Q_flow, Q_flow_int.y) annotation (Line(
      points={{0,-100},{0,-60},{-19,-60}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.T_Air, Air_Temperature.y) annotation (Line(
      points={{0,-100},{0,-60},{19,-60}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5), Text(
      string="%first",
      index=-1,
      extent={{-6,3},{-6,3}},
      horizontalAlignment=TextAlignment.Right));
end v0;
