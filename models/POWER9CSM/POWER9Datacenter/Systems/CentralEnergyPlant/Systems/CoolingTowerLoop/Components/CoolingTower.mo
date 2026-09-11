within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.Components;
model CoolingTower
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (
    port_b_nominal(p=2.4e5, T=20 + 273.15),
    port_a_nominal(
      p=3e5,
      T=20 + 273.15,
      m_flow=100),
    final port_a,
    final port_b);

  parameter Integer nCells=4;

  Modelica.Blocks.Interfaces.RealInput T_ext[nCells](each unit="K") annotation (
      Placement(transformation(
        rotation=270,
        extent={{-20,-20},{20,20}},
        origin={0,120}), iconTransformation(
        extent={{-30,-30},{10,10}},
        rotation=270,
        origin={50,110})));

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
  TRANSFORM.Fluid.Valves.ValveLinear valve[nCells](
    redeclare package Medium = Medium,
    each m_flow_start=31.25,
    each dp_nominal=100,
    each m_flow_nominal=100) annotation (Placement(transformation(
        extent={{10,10},{-10,-10}},
        rotation=180,
        origin={-70,0})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare replaceable model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_b=nCells,
    nPorts_a=1)
               annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-110,0})));
  TRANSFORM.Fluid.Volumes.SimpleVolume plenum_cell[nCells](
    redeclare package Medium = Medium,
    each p_start=port_a_start.p,
    each T_start=port_a_start.T,
    redeclare replaceable model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (each V=0.01)) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-40,0})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet(
    redeclare package Medium = Medium,
    p_start=port_b_start.p,
    T_start=port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_b=1,
    nPorts_a=nCells)
               annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={70,0})));
  Modelica.Blocks.Interfaces.RealInput opening[nCells]
    "=1: completely open, =0: completely closed" annotation (Placement(
        transformation(
        extent={{-20,-20},{20,20}},
        rotation=270,
        origin={-70,120}), iconTransformation(
        extent={{-20,-20},{20,20}},
        rotation=270,
        origin={-40,120})));
  CoolingTowerCell cell[nCells](
    redeclare package Medium = Medium,
    port_a_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_nominal.p,
        T=port_a_nominal.T,
        h=port_a_nominal.h,
        m_flow=port_a_nominal.m_flow/nCells) for i in 1:nCells},
    port_b_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_b_nominal.p,
        T=port_b_nominal.T,
        h=port_b_nominal.h,
        m_flow=port_b_nominal.m_flow/nCells) for i in 1:nCells},
    port_a_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_start.p,
        T=port_a_start.T,
        h=port_a_start.h,
        m_flow=port_a_start.m_flow/nCells) for i in 1:nCells},
    port_b_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_b_start.p,
        T=port_b_start.T,
        h=port_b_start.h,
        m_flow=port_b_start.m_flow/nCells) for i in 1:nCells})
    annotation (Placement(transformation(extent={{-10,-10},{10,10}})));
equation

  connect(port_a, res_inlet.port_a)
    annotation (Line(points={{-180,0},{-157,0}}, color={0,127,255}));
  connect(res_outlet.port_b, port_b)
    annotation (Line(points={{137,0},{180,0}}, color={0,127,255}));
  connect(plenum_inlet.port_b, valve.port_a)
    annotation (Line(points={{-104,0},{-80,0}},  color={0,127,255}));
  connect(res_inlet.port_b, plenum_inlet.port_a[1])
    annotation (Line(points={{-143,0},{-116,0}}, color={0,127,255}));
  connect(valve.port_b, plenum_cell.port_a)
    annotation (Line(points={{-60,0},{-46,0}}, color={0,127,255}));
  connect(valve.opening, opening)
    annotation (Line(points={{-70,8},{-70,120}}, color={0,0,127}));
  connect(plenum_outlet.port_b[1], res_outlet.port_a)
    annotation (Line(points={{76,0},{123,0}}, color={0,127,255}));
  connect(plenum_cell.port_b, cell.port_a)
    annotation (Line(points={{-34,0},{-10,0}}, color={0,127,255}));
  connect(cell.port_b, plenum_outlet.port_a)
    annotation (Line(points={{10,0},{64,0}}, color={0,127,255}));
  connect(cell.T_ext, T_ext)
    annotation (Line(points={{0,12},{0,120}}, color={0,0,127}));
  annotation (Icon(graphics={
        Rectangle(
          extent={{-100,100},{100,-100}},
          lineColor={28,108,200},
          fillColor={255,255,255},
          fillPattern=FillPattern.Solid),
        Polygon(
          points={{-60,20},{-20,-20},{-20,-18},{-20,20},{-60,-20},{-60,20}},
          lineColor={28,108,200},
          fillColor={28,108,200},
          fillPattern=FillPattern.Solid),
        Line(points={{-100,0},{100,0}}, color={28,108,200}),
        Line(points={{-40,100},{-40,2}}, color={28,108,200}),
        Line(points={{40,100},{40,20}}, color={28,108,200}),
        Rectangle(
          extent={{20,20},{60,-20}},
          lineColor={28,108,200},
          fillColor={28,108,200},
          fillPattern=FillPattern.Solid)}), Diagram(coordinateSystem(
          preserveAspectRatio=false, extent={{-180,-100},{180,100}})));
end CoolingTower;
