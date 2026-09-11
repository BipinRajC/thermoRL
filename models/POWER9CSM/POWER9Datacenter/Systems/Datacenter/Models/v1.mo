within POWER9Datacenter.Systems.Datacenter.Models;
model v1
  import TRANSFORM.Units.Conversions.Functions.Pressure_Pa.from_psi;
  import TRANSFORM.Units.Conversions.Functions.Pressure_Pa.from_bar;
  import
    TRANSFORM.Units.Conversions.Functions.Temperature_K.from_degC;
  import
    TRANSFORM.Units.Conversions.Functions.VolumeFlowRate_m3_s.from_gpm;

  extends
    POWER9Datacenter.Systems.Datacenter.BaseClasses.BaseClasses_A.PartialModel_A
                                                                          (
    port_b_nominal(p=from_psi(59.7), T=from_degC(35.0)),
    port_a_nominal(
      p=from_psi(79.7),
      T=from_degC(22.5),
      m_flow=from_gpm(1900.0)),
    redeclare replaceable Controls.CS_Constant controls,
    redeclare replaceable Data.NULL data,
    redeclare replaceable Sources.NULL sources,
    summary(m_flow_prim=sensor_m_flow.m_flow));

  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_a=1,
    nPorts_b=structure.computeBlock.n_int + 1)
    annotation (Placement(transformation(extent={{-70,-10},{-50,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet(
    redeclare package Medium = Medium,
    p_start=port_b_start.p,
    T_start=port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_a=structure.computeBlock.n_int + 1,
    nPorts_b=1)
    annotation (Placement(transformation(extent={{50,-10},{70,10}})));
  replaceable Systems.CoolingBlock.Models.v1 computeBlock[
    structure.computeBlock.n_int] constrainedby
    Systems.CoolingBlock.BaseClasses.BaseClasses_A.PartialModel_A(
      redeclare package Medium = Medium) annotation (Placement(
        transformation(extent={{-10,-10},{10,10}})), choicesAllMatching
      =true);

  TRANSFORM.Fluid.Valves.ValveLinear valve_bypass(
    redeclare package Medium = Medium,
    dp_start(displayUnit="Pa") = 50,
    m_flow_start=10,
    dp_nominal(displayUnit="Pa") = port_a_nominal.p - port_b_nominal.p,
    m_flow_nominal=port_a_nominal.m_flow) "from_psi(10.0)"
    annotation (Placement(transformation(extent={{-10,40},{10,60}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance
    resistance_inlet(redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow) annotation (Placement(transformation(
          extent={{-100,-10},{-80,10}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance
    resistance_outlet(redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow) annotation (Placement(transformation(
          extent={{80,-10},{100,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_toComputeBlocks(redeclare
      package Medium = Medium, final nParallel=structure.computeBlock.n)
    if structure.computeBlock.useParallel
    annotation (Placement(transformation(extent={{-40,-10},{-20,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_fromComputeBlocks(redeclare
      package Medium = Medium, final nParallel=structure.computeBlock.n)
    if structure.computeBlock.useParallel
    annotation (Placement(transformation(extent={{40,-10},{20,10}})));

  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_bypass(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e5)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{20,40},{40,60}})));
  TRANSFORM.Fluid.Sensors.MassFlowRate sensor_m_flow(redeclare package Medium
      = Medium)
    annotation (Placement(transformation(extent={{-140,-10},{-120,10}})));
  TRANSFORM.Fluid.Sensors.PressureTemperatureTwoPort sensor_pT(redeclare
      package Medium = Medium)
    annotation (Placement(transformation(extent={{118,-10},{138,10}})));
equation
  connect(resistance_inlet.port_b, plenum_inlet.port_a[1])
    annotation (Line(points={{-83,0},{-66,0}}, color={0,127,255}));
  connect(controlBus.opening_bypass, valve_bypass.opening) annotation (Line(
      points={{0,100},{0,58}},
      color={255,204,51},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(plenum_outlet.port_b[1], resistance_outlet.port_a)
    annotation (Line(points={{66,0},{83,0}}, color={0,127,255}));

  connect(plenum_inlet.port_b[1], valve_bypass.port_a);
  connect(plenum_outlet.port_a[1], resistance_bypass.port_b);
  for i in 1:structure.computeBlock.n_int loop
    if structure.computeBlock.useParallel then
      connect(plenum_inlet.port_b[i + 1], nFlow_toComputeBlocks.port_1);
      connect(nFlow_toComputeBlocks.port_n, computeBlock[i].port_a);

      connect(computeBlock[i].port_b, nFlow_fromComputeBlocks.port_n);
      connect(nFlow_fromComputeBlocks.port_1, plenum_outlet.port_a[i +
        1]);
    else
      connect(plenum_inlet.port_b[i + 1], computeBlock[i].port_a);

      connect(computeBlock[i].port_b, plenum_outlet.port_a[i + 1]);
    end if;
  end for;

  connect(valve_bypass.port_b, resistance_bypass.port_a)
    annotation (Line(points={{10,50},{23,50}}, color={0,127,255}));
  connect(port_a, sensor_m_flow.port_a)
    annotation (Line(points={{-180,0},{-140,0}}, color={0,127,255}));
  connect(sensor_m_flow.port_b, resistance_inlet.port_a)
    annotation (Line(points={{-120,0},{-97,0}}, color={0,127,255}));
  connect(controlBus.m_flow_supply, sensor_m_flow.m_flow) annotation (Line(
      points={{0,100},{-130,100},{-130,3.6}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(resistance_outlet.port_b, sensor_pT.port_a)
    annotation (Line(points={{97,0},{118,0}}, color={0,127,255}));
  connect(sensor_pT.port_b, port_b)
    annotation (Line(points={{138,0},{180,0}}, color={0,127,255}));
end v1;
