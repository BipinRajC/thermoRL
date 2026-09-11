within POWER9Datacenter.Components;
model PumpTrain
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (final port_a, final port_b);
  TRANSFORM.Fluid.Valves.ValveLinear valve(
    redeclare package Medium = Medium,
    dp_start=500,
    dp_nominal=1000,
    m_flow_nominal=port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{-50,-10},{-30,10}})));
  TRANSFORM.Fluid.Volumes.SimpleVolume volume(
    redeclare package Medium = Medium,
    p_start=pump.p_a_start,
    T_start=pump.T_a_start,
    redeclare replaceable model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01)) annotation (Placement(transformation(extent={{10,-10},{-10,10}},
          rotation=180)));
  TRANSFORM.Fluid.Machines.Pump_Controlled pump(
    redeclare package Medium = Medium,
    p_a_start=port_a_start.p,
    p_b_start=port_b_start.p,
    T_a_start=port_a_start.T,
    T_b_start=port_b_start.T,
    m_flow_start=port_a_start.m_flow,
    m_flow_nominal=port_a_start.m_flow,
    final use_port=true,
    k_inputSignal=pump.N_nominal)
                         annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={40,0})));
  Modelica.Blocks.Interfaces.RealInput opening
    "=1: completely open, =0: completely closed" annotation (Placement(
        transformation(
        extent={{-20,-20},{20,20}},
        rotation=270,
        origin={-40,120})));
  Modelica.Blocks.Interfaces.RealInput N annotation (Placement(transformation(
        extent={{-20,-20},{20,20}},
        rotation=270,
        origin={40,120})));
equation
  connect(valve.opening, opening) annotation (Line(points={{-40,8},{-40,120}},
                          color={0,0,127}));
  connect(pump.inputSignal, N) annotation (Line(points={{40,7},{40,120}},
                    color={0,0,127}));
  connect(valve.port_b, volume.port_a)
    annotation (Line(points={{-30,0},{-6,0}}, color={0,127,255}));
  connect(volume.port_b, pump.port_a)
    annotation (Line(points={{6,0},{30,0}}, color={0,127,255}));
  connect(valve.port_a, port_a)
    annotation (Line(points={{-50,0},{-180,0}}, color={0,127,255}));
  connect(pump.port_b, port_b)
    annotation (Line(points={{50,0},{180,0}}, color={0,127,255}));
  annotation (Icon(coordinateSystem(preserveAspectRatio=false), graphics={
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
        Ellipse(
          extent={{60,20},{20,-20}},
          lineColor={28,108,200},
          fillColor={28,108,200},
          fillPattern=FillPattern.Solid),
        Line(points={{-100,0},{100,0}}, color={28,108,200}),
        Line(points={{-40,100},{-40,2}}, color={28,108,200}),
        Line(points={{40,100},{40,20}}, color={28,108,200})}),   Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end PumpTrain;
