within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.IntermediateLoop.Models;
model v0
  extends BaseClasses.BaseClasses_A.PartialModel_A(
    final port_a1,
    final port_b1,
    final port_a2,
    final port_b2,
    port_a1_nominal(
      p=3.837e5,
      T=302.15,
      m_flow=300.0),
    port_b1_nominal(p=5.4951e5, T=294.15),
    port_a2_nominal(
      p=2.9e5,
      T=293.15,
      m_flow=500.0),
    port_b2_nominal(p=2.6e5, T=297.95),
    port_b1_start=port_b1_nominal,
    port_b2_start=port_b2_nominal,
    redeclare replaceable Controls.CS_Constant
      controls,
    redeclare replaceable Sources.NULL sources,
    redeclare replaceable Data.NULL data);

    parameter Integer nPumpTrains = 4;
    parameter Integer nHeatExchangerTrains = 4;

  TRANSFORM.HeatExchangers.Simple_HX heatExchanger[nHeatExchangerTrains](
    redeclare package Medium_1 = Medium_1,
    redeclare package Medium_2 = Medium_2,
    each V_1=1,
    each V_2=1,
    each UA=1e5,
    each p_a_start_1=port_a1_start.p,
    each T_a_start_1=port_a1_start.T,
    each m_flow_start_1=port_a1_start.m_flow,
    each p_a_start_2=port_a2_start.p,
    each T_a_start_2=port_a2_start.T,
    each m_flow_start_2=port_a2_start.m_flow)
    annotation (Placement(transformation(extent={{-10,-66},{10,-46}})));
  TRANSFORM.Fluid.FittingsAndResistances.PressureLoss resistance_heatExchanger_hot[
    nHeatExchangerTrains](redeclare package Medium = Medium_1, each dp0=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/(
        port_a1_nominal.m_flow/nHeatExchangerTrains))
    annotation (Placement(transformation(extent={{-74,-10},{-54,10}})));
  TRANSFORM.Fluid.Valves.ValveLinear valve_heatExchanger_hot[
    nHeatExchangerTrains](
    redeclare package Medium = Medium_1,
    each dp_start(displayUnit="Pa") = 50,
    each m_flow_start=75,
    each dp_nominal(displayUnit="Pa") = 100,
    each m_flow_nominal=port_a1_nominal.m_flow/nHeatExchangerTrains)
    annotation (Placement(transformation(extent={{-40,-10},{-20,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_pump(
    redeclare package Medium = Medium_1,
    p_start=port_a1_start.p,
    T_start=port_a1_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_b=nHeatExchangerTrains,
    nPorts_a=nPumpTrains)
                annotation (Placement(transformation(
        extent={{-10,10},{10,-10}},
        rotation=0,
        origin={-40,60})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_heatExchanger_hot(
    redeclare package Medium = Medium_1,
    p_start=port_b1_start.p,
    T_start=port_b1_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_a=nHeatExchangerTrains,
    nPorts_b=2) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={50,0})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet(
      redeclare package Medium = Medium_1, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a1_nominal.m_flow)                                    annotation (
      Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-150,60})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet(
    redeclare package Medium = Medium_1,
    p_start=port_a1_start.p,
    T_start=port_a1_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_a=1,
    nPorts_b=nPumpTrains)
                annotation (Placement(transformation(
        extent={{10.5,-10.25},{-10.5,10.25}},
        rotation=180,
        origin={-119.5,59.75})));
  TRANSFORM.Fluid.Valves.ValveLinear valve_heatExchanger_cold[
    nHeatExchangerTrains](
    redeclare package Medium = Medium_2,
    each dp_start(displayUnit="Pa") = 50,
    each m_flow_start=100,
    each dp_nominal(displayUnit="Pa") = 100,
    each m_flow_nominal=port_a2_nominal.m_flow/nHeatExchangerTrains)
    annotation (Placement(transformation(extent={{50,-70},{30,-50}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet_2(
    redeclare package Medium = Medium_2,
    p_start=port_a2_start.p,
    T_start=port_a2_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01),
    nPorts_a=1,
    nPorts_b=nHeatExchangerTrains)
                annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={100,-60})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet_2(
    redeclare package Medium = Medium_2,
    p_start=port_b2_start.p,
    T_start=port_b2_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01),
    nPorts_b=1,
    nPorts_a=nHeatExchangerTrains)
                annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={-80,-60})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_outlet_2(
      redeclare package Medium = Medium_2, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a2_nominal.m_flow)                    annotation (Placement(
        transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={-140,-60})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet_2(
      redeclare package Medium = Medium_2, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e3)/
        port_a2_nominal.m_flow)                    annotation (Placement(
        transformation(
        extent={{10,-10},{-10,10}},
        rotation=0,
        origin={140,-60})));
  POWER9Datacenter.Components.PumpTrain pumpTrain[nPumpTrains](
    redeclare package Medium = Medium_1,
    port_a_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a1_nominal.p,
        T=port_a1_nominal.T,
        h=port_a1_nominal.h,
        m_flow=port_a1_nominal.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_b_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a1_nominal.p,
        T=port_a1_nominal.T,
        h=port_a1_nominal.h,
        m_flow=port_a1_nominal.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_a_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a1_start.p,
        T=port_a1_start.T,
        h=port_a1_start.h,
        m_flow=port_a1_start.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_b_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a1_start.p + 1e5,
        T=port_a1_start.T,
        h=port_a1_start.h,
        m_flow=port_a1_start.m_flow/nPumpTrains) for i in 1:nPumpTrains})
    annotation (Placement(transformation(extent={{-90,50},{-70,70}})));
  TRANSFORM.Fluid.Volumes.ExpansionTank_1Port tank(
    redeclare package Medium = Medium_1,
    A=Modelica.Constants.pi*0.5^2,
    V0=10,
    p_surface(displayUnit="bar"),
    p_start(displayUnit="bar") = port_b1_start.p,
    level_start=1.0,
    T_start=293.15) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={70,72})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance res_press(
      redeclare package Medium = Medium_1, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e5)/
        port_a1_nominal.m_flow) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=90,
        origin={70,42})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance res_outlet(
      redeclare package Medium = Medium_1, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(0.5e5)/
        port_a1_nominal.m_flow)
    annotation (Placement(transformation(extent={{120,50},{140,70}})));
equation
  connect(valve_heatExchanger_hot.port_b, heatExchanger.port_a1) annotation (
      Line(points={{-20,0},{-14,0},{-14,-52},{-10,-52}}, color={0,127,255}));

  connect(heatExchanger.port_a2, valve_heatExchanger_cold.port_b)
    annotation (Line(points={{10,-60},{30,-60}}, color={0,127,255}));
  connect(resistance_inlet.port_a, port_a1)
    annotation (Line(points={{-157,60},{-180,60}}, color={0,127,255}));
  connect(plenum_inlet.port_a[1], resistance_inlet.port_b) annotation (Line(
        points={{-125.8,59.75},{-128,60},{-143,60}}, color={0,127,255}));

  connect(resistance_heatExchanger_hot.port_b, valve_heatExchanger_hot.port_a)
    annotation (Line(points={{-57,0},{-40,0}}, color={0,127,255}));
  connect(controlBus.opening_valve_heatExchanger_hot, valve_heatExchanger_hot.opening) annotation (
      Line(
      points={{0,100},{-180,100},{-180,20},{-30,20},{-30,8}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.opening_valve_heatExchanger_cold, valve_heatExchanger_cold.opening) annotation (
      Line(
      points={{0,100},{180,100},{180,-40},{40,-40},{40,-52}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(resistance_outlet_2.port_b, port_b2)
    annotation (Line(points={{-147,-60},{-180,-60}}, color={0,127,255}));
  connect(resistance_outlet_2.port_a, plenum_outlet_2.port_b[1])
    annotation (Line(points={{-133,-60},{-86,-60}}, color={0,127,255}));
  connect(port_a2, resistance_inlet_2.port_a)
    annotation (Line(points={{180,-60},{147,-60}}, color={0,127,255}));
  connect(resistance_inlet_2.port_b, plenum_inlet_2.port_a[1])
    annotation (Line(points={{133,-60},{106,-60}}, color={0,127,255}));
  connect(plenum_pump.port_b, resistance_heatExchanger_hot.port_a) annotation (
      Line(points={{-34,60},{20,60},{20,40},{-80,40},{-80,0},{-71,0}},
                                                                     color={0,127,
          255}));
  connect(heatExchanger.port_b1, plenum_heatExchanger_hot.port_a) annotation (
      Line(points={{10,-52},{20,-52},{20,0},{44,0}}, color={0,127,255}));
  connect(heatExchanger.port_b2, plenum_outlet_2.port_a)
    annotation (Line(points={{-10,-60},{-74,-60}}, color={0,127,255}));
  connect(valve_heatExchanger_cold.port_a, plenum_inlet_2.port_b)
    annotation (Line(points={{50,-60},{94,-60}}, color={0,127,255}));
  connect(controlBus.opening_pumpTrain, pumpTrain.opening) annotation (Line(
      points={{0,100},{-84,100},{-84,72}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.N_pumpTrain, pumpTrain.N) annotation (Line(
      points={{0,100},{-76,100},{-76,72}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(plenum_inlet.port_b, pumpTrain.port_a) annotation (Line(points={{-113.2,
          59.75},{-101.6,59.75},{-101.6,60},{-90,60}}, color={0,127,255}));
  connect(pumpTrain.port_b, plenum_pump.port_a)
    annotation (Line(points={{-70,60},{-46,60}}, color={0,127,255}));
  connect(res_press.port_b, tank.port)
    annotation (Line(points={{70,49},{70,63.6}}, color={0,127,255}));
  connect(plenum_heatExchanger_hot.port_b[1], res_outlet.port_a) annotation (
      Line(points={{56,-0.25},{100,-0.25},{100,60},{123,60}}, color={0,127,255}));
  connect(res_outlet.port_b, port_b1)
    annotation (Line(points={{137,60},{180,60}}, color={0,127,255}));
  connect(res_press.port_a, plenum_heatExchanger_hot.port_b[2])
    annotation (Line(points={{70,35},{70,0.25},{56,0.25}}, color={0,127,255}));
end v0;
