within POWER9Datacenter.Systems.Datacenter.Controls;
model CS_Constant
  extends BaseClasses.PartialControls(redeclare replaceable Data.NULL data);

  Modelica.Blocks.Sources.Constant const(k=1)
    annotation (Placement(transformation(extent={{-40,10},{-20,-10.5}})));
equation
  connect(controlBus.opening_bypass, const.y) annotation (Line(
      points={{0,-100},{0,-0.25},{-19,-0.25}},
      color={255,204,51},
      pattern=LinePattern.Dash,
      thickness=0.5));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end CS_Constant;
