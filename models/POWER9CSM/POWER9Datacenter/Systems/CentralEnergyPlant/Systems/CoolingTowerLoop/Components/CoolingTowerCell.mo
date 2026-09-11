within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.Components;
model CoolingTowerCell
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (
    port_b_nominal(p=2.4e5, T=20 + 273.15),
    port_a_nominal(
      p=3e5,
      T=20 + 273.15,
      m_flow=25),
    final port_a,
    final port_b);

  TRANSFORM.Fluid.Volumes.SimpleVolume cell(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare replaceable model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    use_HeatPort=true) annotation (Placement(transformation(extent={{10,-10},{-10,
            10}}, rotation=180)));
  TRANSFORM.HeatAndMassTransfer.Resistances.Heat.Specified_Resistance heatTransfer(R_val=
        1e-10) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=90,
        origin={0,30})));
  TRANSFORM.HeatAndMassTransfer.BoundaryConditions.Heat.Temperature boundary(use_port=
        true) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=270,
        origin={0,56})));
  Modelica.Blocks.Interfaces.RealInput T_ext(unit="K") annotation (Placement(
        transformation(
        rotation=270,
        extent={{-20,-20},{20,20}},
        origin={0,120}), iconTransformation(
        extent={{-20,-20},{20,20}},
        rotation=270,
        origin={0,120})));

  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance res_inlet(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{-160,-10},{-140,10}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance res_outlet(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{120,-10},{140,10}})));
equation

  connect(port_a, res_inlet.port_a)
    annotation (Line(points={{-180,0},{-157,0}}, color={0,127,255}));
  connect(res_outlet.port_b, port_b)
    annotation (Line(points={{137,0},{180,0}}, color={0,127,255}));
  connect(heatTransfer.port_b, boundary.port)
    annotation (Line(points={{0,37},{0,46}}, color={191,0,0}));
  connect(heatTransfer.port_a, cell.heatPort)
    annotation (Line(points={{0,23},{0,6}}, color={191,0,0}));
  connect(boundary.T_ext, T_ext)
    annotation (Line(points={{0,60},{0,60},{0,120}}, color={0,0,127}));
  connect(res_inlet.port_b, cell.port_a)
    annotation (Line(points={{-143,0},{-6,0}}, color={0,127,255}));
  connect(cell.port_b, res_outlet.port_a)
    annotation (Line(points={{6,0},{123,0}}, color={0,127,255}));
  annotation (Icon(graphics={
        Rectangle(
          extent={{-100,100},{100,-100}},
          lineColor={28,108,200},
          fillColor={255,255,255},
          fillPattern=FillPattern.Solid),
        Rectangle(
          extent={{-20,20},{20,-20}},
          lineColor={28,108,200},
          fillColor={28,108,200},
          fillPattern=FillPattern.Solid),
        Line(points={{0,100},{0,20}},   color={28,108,200}),
        Line(points={{-100,0},{100,0}}, color={28,108,200})}));
end CoolingTowerCell;
