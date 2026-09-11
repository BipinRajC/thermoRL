within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.Cabinet.Models;
model v1

  import TRANSFORM.Units.Conversions.Functions.Pressure_Pa.from_psi;
  import TRANSFORM.Units.Conversions.Functions.Temperature_K.from_degC;

  extends BaseClasses.BaseClasses_A.PartialModel_A(
    port_a_nominal(
      p=from_psi(64.7),
      T=from_degC(30.0),
      m_flow=17),
    redeclare replaceable Data.NULL data,
    redeclare replaceable Sources.v0 sources,
    redeclare replaceable Controls.NULL controls);

  TRANSFORM.HeatAndMassTransfer.BoundaryConditions.Heat.HeatFlow boundary(
      use_port=true) annotation (Placement(transformation(
        extent={{10,10},{-10,-10}},
        rotation=90,
        origin={-40,36})));
  TRANSFORM.Fluid.Volumes.SimpleVolume volume(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    use_HeatPort=true) annotation (Placement(transformation(extent={{-10,10},{10,
            -10}}, rotation=0)));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet(
      redeclare package Medium = Medium, R=5000)
    annotation (Placement(transformation(extent={{-70,-10},{-50,10}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_outlet(
      redeclare package Medium = Medium, R=5000)
    annotation (Placement(transformation(extent={{50,-10},{70,10}})));

  Modelica.Thermal.HeatTransfer.Components.Convection convection annotation (
      Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=90,
        origin={40,36})));
  Modelica.Thermal.HeatTransfer.Sources.PrescribedTemperature
    prescribedTemperature annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=-90,
        origin={40,70})));
  Modelica.Blocks.Sources.RealExpression heatTransCoef(y=summary.htc)
    annotation (Placement(transformation(extent={{-2,26},{18,46}})));
equation
  connect(boundary.port, volume.heatPort)
    annotation (Line(points={{-40,26},{-40,16},{0,16},{0,6}},
                                            color={191,0,0}));
  connect(port_a, resistance_inlet.port_a)
    annotation (Line(points={{-180,0},{-67,0}}, color={0,127,255}));
  connect(resistance_inlet.port_b, volume.port_a)
    annotation (Line(points={{-53,0},{-6,0}}, color={0,127,255}));
  connect(volume.port_b, resistance_outlet.port_a)
    annotation (Line(points={{6,0},{53,0}}, color={0,127,255}));
  connect(resistance_outlet.port_b, port_b)
    annotation (Line(points={{67,0},{180,0}}, color={0,127,255}));
  connect(controlBus.Q_flow, boundary.Q_flow_ext) annotation (Line(
      points={{0,100},{-40,100},{-40,40}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(convection.solid, volume.heatPort)
    annotation (Line(points={{40,26},{40,16},{0,16},{0,6}}, color={191,0,0}));
  connect(prescribedTemperature.port,convection. fluid)
    annotation (Line(points={{40,60},{40,46}}, color={191,0,0}));
  connect(controlBus.T_Air,prescribedTemperature. T) annotation (Line(
      points={{0,100},{40,100},{40,82}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5), Text(
      string="%first",
      index=-1,
      extent={{-6,3},{-6,3}},
      horizontalAlignment=TextAlignment.Right));
  connect(heatTransCoef.y, convection.Gc)
    annotation (Line(points={{19,36},{30,36}}, color={0,0,127}));
end v1;
