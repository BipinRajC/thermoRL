within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.Models;
model v0
  extends BaseClasses.BaseClasses_A.PartialModel_A(
    port_a_nominal(
      p=2.6e5,
      T=30+273.15,
      m_flow=500.0),
    port_b_nominal(p=2.9e5, T=293.15),
    redeclare replaceable Data.NULL data,
    redeclare replaceable Controls.CS_Constant controls,
    redeclare replaceable Sources.v0 sources);

  parameter Integer nCoolingTowers=4;
  parameter Integer nPumpTrains=4;

  TRANSFORM.Fluid.Volumes.MixingVolume plenum_pump_outlet(
    redeclare package Medium = Medium,
    p_start=port_b_start.p,
    T_start=port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_b=1,
    nPorts_a=nPumpTrains) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={110,0})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_outlet(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{130,-10},{150,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_pump_inlet(
    redeclare package Medium = Medium,
    p_start=plenum_outlet.p_start,
    T_start=plenum_outlet.T_start,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01),
    nPorts_a=1,
    nPorts_b=nPumpTrains) annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={40,0})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_to_pump(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{0,-10},{20,10}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e4)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{-150,-10},{-130,10}})));
  TRANSFORM.Fluid.Volumes.ExpansionTank_1Port basin_reservoir(
    redeclare package Medium = Medium,
    A=Modelica.Constants.pi*1.0^2,
    V0=20.0,
    p_surface(displayUnit="bar"),
    p_start(displayUnit="bar") = 2.5e5,
    level_start=0.5,
    use_T_start=true,
    T_start=293.15)
    "Basin reservoir at Atmospheric pressure" annotation (
      Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=0,
        origin={-20,50})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance res_basin(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e5)/
        port_a_nominal.m_flow) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=90,
        origin={-20,20})));
  POWER9Datacenter.Components.PumpTrain pumpTrain[nPumpTrains](
    redeclare package Medium = Medium,
    port_a_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_nominal.p,
        T=port_a_nominal.T,
        h=port_a_nominal.h,
        m_flow=port_a_nominal.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_b_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_b_nominal.p,
        T=port_b_nominal.T,
        h=port_b_nominal.h,
        m_flow=port_b_nominal.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_a_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=plenum_pump_inlet.p_start,
        T=port_a_start.T,
        h=port_a_start.h,
        m_flow=port_a_start.m_flow/nPumpTrains) for i in 1:nPumpTrains},
    port_b_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_b_start.p,
        T=port_b_start.T,
        h=port_b_start.h,
        m_flow=port_b_start.m_flow/nPumpTrains) for i in 1:nPumpTrains})
    annotation (Placement(transformation(extent={{60,-10},{80,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=50),
    nPorts_a=1,
    nPorts_b=nCoolingTowers)  annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-100,0})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet(
    redeclare package Medium = Medium,
    p_start=coolingTower[1].port_b_start.p,
    T_start=coolingTower[1].port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=1),
    nPorts_b=2,
    nPorts_a=nCoolingTowers)
               annotation (Placement(transformation(
        extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-40,0})));
  Components.CoolingTower coolingTower[nCoolingTowers](redeclare package Medium
      = Medium,
    port_a_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_nominal.p,
        T=port_a_nominal.T,
        h=port_a_nominal.h,
        m_flow=port_a_nominal.m_flow/nCoolingTowers) for i in 1:nCoolingTowers},
    port_b_nominal={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_nominal.p - 1e5,
        T=port_b_nominal.T,
        h=port_b_nominal.h,
        m_flow=port_a_nominal.m_flow/nCoolingTowers) for i in 1:nCoolingTowers},
    port_a_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_start.p,
        T=port_a_start.T,
        h=port_a_start.h,
        m_flow=port_a_start.m_flow/nCoolingTowers) for i in 1:nCoolingTowers},
    port_b_start={TRANSFORM.Examples.Utilities.Record_fluidPorts(
        p=port_a_start.p - 1e5,
        T=port_b_start.T,
        h=port_b_start.h,
        m_flow=port_b_start.m_flow/nCoolingTowers) for i in 1:nCoolingTowers})
                                                       annotation (Placement(
        transformation(rotation=0, extent={{-80,-10},{-60,10}})));
equation

  connect(port_b, resistance_outlet.port_b)
    annotation (Line(points={{180,0},{147,0}}, color={0,127,255}));

  connect(plenum_pump_outlet.port_b[1], resistance_outlet.port_a)
    annotation (Line(points={{116,0},{133,0}}, color={0,127,255}));
  connect(resistance_to_pump.port_b, plenum_pump_inlet.port_a[1])
    annotation (Line(points={{17,0},{34,0}},  color={0,127,255}));
  connect(port_a, resistance_inlet.port_a)
    annotation (Line(points={{-180,0},{-147,0}}, color={0,127,255}));
  connect(res_basin.port_b, basin_reservoir.port)
    annotation (Line(points={{-20,27},{-20,41.6}}, color={0,127,255}));
  connect(pumpTrain.port_b, plenum_pump_outlet.port_a)
    annotation (Line(points={{80,0},{104,0}}, color={0,127,255}));
  connect(pumpTrain.port_a, plenum_pump_inlet.port_b)
    annotation (Line(points={{60,0},{46,0}}, color={0,127,255}));
  connect(plenum_outlet.port_b[1], resistance_to_pump.port_a) annotation (Line(
        points={{-34,0.25},{-16,0.25},{-16,0},{3,0}}, color={0,127,255}));
  connect(res_basin.port_a, plenum_outlet.port_b[2]) annotation (Line(points={{-20,
          13},{-20,-0.25},{-34,-0.25}}, color={0,127,255}));
  connect(resistance_inlet.port_b, plenum_inlet.port_a[1])
    annotation (Line(points={{-133,0},{-106,0}}, color={0,127,255}));
  connect(plenum_inlet.port_b, coolingTower.port_a)
    annotation (Line(points={{-94,0},{-80,0}}, color={0,127,255}));
  connect(coolingTower.port_b, plenum_outlet.port_a)
    annotation (Line(points={{-60,0},{-46,0}}, color={0,127,255}));
  connect(controlBus.opening_coolingTower, coolingTower.opening) annotation (
      Line(
      points={{0,100},{-74,100},{-74,12}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.opening_pumpTrain, pumpTrain.opening) annotation (Line(
      points={{0,100},{66,100},{66,12}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.N_pumpTrain, pumpTrain.N) annotation (Line(
      points={{0,100},{74,100},{74,12}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.T_ext_coolingTower, coolingTower.T_ext) annotation (Line(
      points={{0,100},{-66,100},{-66,12}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
end v0;
