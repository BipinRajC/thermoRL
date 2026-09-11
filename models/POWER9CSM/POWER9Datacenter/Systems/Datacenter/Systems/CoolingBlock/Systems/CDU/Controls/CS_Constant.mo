within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Controls;
model CS_Constant
  extends BaseClasses.PartialControls(redeclare replaceable Data.NULL
      data);

  Modelica.Blocks.Sources.Constant opening_valve(k=0.5)
                         annotation (Placement(transformation(
          extent={{-40,-60},{-20,-40}})));
  Modelica.Blocks.Sources.Constant Nrel_pump(k=1)
    annotation (Placement(transformation(extent={{-40,-30},{-20,-10}})));
equation
  connect(controlBus.opening_valve, opening_valve.y) annotation (Line(
      points={{0,-100},{0,-50},{-19,-50}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.Nrel_pump, Nrel_pump.y) annotation (Line(
      points={{0,-100},{0,-20},{-19,-20}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
end CS_Constant;
