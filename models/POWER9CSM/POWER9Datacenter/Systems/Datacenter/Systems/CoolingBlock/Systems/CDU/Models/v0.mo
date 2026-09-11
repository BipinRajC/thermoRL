within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Models;
model v0

  import TRANSFORM.Units.Conversions.Functions.Pressure_Pa.from_psi;
  import TRANSFORM.Units.Conversions.Functions.Temperature_K.from_degC;

  extends BaseClasses.BaseClasses_A.PartialModel_A(
    port_a2_nominal(
      p=from_psi(64.7),
      T=from_degC(40.0),
      m_flow=17),
    port_a1_nominal(
      p=from_psi(30.5),
      T=from_degC(30.0),
      m_flow=15),
    port_b2_nominal(p=port_a2_nominal.p + 1e5),
    port_b1_nominal(p=port_a1_nominal.p - 1e5),
    port_b1_start=port_b1_nominal,
    port_b2_start=port_b2_nominal,
    redeclare replaceable Controls.CS_SimplePI controls,
    redeclare replaceable Data.NULL data,
    redeclare replaceable Sources.NULL sources,
    summary(
      m_flow_prim=port_a1.m_flow,
      m_flow_sec=heatExchanger.port_a1.m_flow,
      W_flow_CDUP=pump.W*pump.nParallel,
      T_prim_s=FacSup_pT.T,
      T_prim_r=FacRet_pT.T,
      T_sec_s=CabSup_pT.T,
      T_sec_r=CabRet_pT.T,
      p_prim_s=FacSup_pT.p,
      p_prim_r=FacRet_pT.p,
      p_sec_s=CabSup_pT.p,
      p_sec_r=CabRet_pT.p));

  TRANSFORM.HeatExchangers.Simple_HX heatExchanger(
    redeclare package Medium_1 = Medium_2,
    redeclare package Medium_2 = Medium_1,
    V_1=0.5,
    V_2=0.5,
    UA=3e3,
    p_a_start_1=port_a2_start.p,
    T_a_start_1=port_a2_start.T,
    m_flow_start_1=port_a2_start.m_flow,
    p_a_start_2=port_a1_start.p,
    T_a_start_2=port_a1_start.T,
    m_flow_start_2=port_a1_start.m_flow,
    R_1=TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a2_nominal.m_flow,
    R_2=TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e5)/
        port_a1_nominal.m_flow)
    annotation (Placement(transformation(extent={{10,66},{-10,46}})));
  TRANSFORM.Fluid.Machines.Pump_Controlled pump(
    redeclare package Medium = Medium_2,
    nParallel=2,
    p_a_start=210000,
    p_b_start=310000,
    T_a_start=303.15,
    m_flow_start=15,
    m_flow_nominal=port_a2_nominal.m_flow,
    use_port=true,
    k_inputSignal=pump.N_nominal)
    annotation (Placement(transformation(extent={{-90,-70},{-110,-50}})));

  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance
    resistance_outlet_1(redeclare package Medium = Medium_1, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a1_nominal.m_flow)
    annotation (Placement(transformation(extent={{100,50},{120,70}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet_1(
     redeclare package Medium = Medium_1, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a1_nominal.m_flow)
    annotation (Placement(transformation(extent={{-120,50},{-100,70}})));

  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_inlet_2(
     redeclare package Medium = Medium_2, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a2_nominal.m_flow)
    annotation (Placement(transformation(extent={{110,-70},{90,-50}})));
  TRANSFORM.Fluid.Volumes.ExpansionTank_1Port tank(
    redeclare package Medium = Medium_2,
    A=Modelica.Constants.pi*1^2,
    p_start=100000,
    level_start=0.5,
    h_start=Medium_2.specificEnthalpy_pT(tank.p_start, port_a1_start.T))
    annotation (Placement(transformation(extent={{-50,-20},{-70,0}})));
  TRANSFORM.Fluid.FittingsAndResistances.TeeJunctionVolume tee(
    redeclare package Medium = Medium_2,
    V=0.1,
    p_start=port_a2_start.p,
    T_start=port_a2_start.T,
    h_start=Medium_2.specificEnthalpy_pT(tank.p_start, port_a1_start.T))
    annotation (Placement(transformation(extent={{-50,-70},{-70,-50}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance resistance_tank(
      redeclare package Medium = Medium_2, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1e5)/
        port_a2_nominal.m_flow) annotation (Placement(transformation(
        extent={{-10,-10},{10,10}},
        rotation=90,
        origin={-60,-36})));
  TRANSFORM.Fluid.Valves.ValveLinear valve(
    redeclare package Medium = Medium_1,
    dp_start(displayUnit="Pa") = 50,
    m_flow_start=10,
    dp_nominal(displayUnit="Pa") = 0.5e5,
    m_flow_nominal=port_a1_nominal.m_flow)
    annotation (Placement(transformation(extent={{-80,50},{-60,70}})));
  TRANSFORM.Fluid.Sensors.PressureTemperature CabSup_pT(
    redeclare package Medium =
        TemplatesCSM.BaseClasses.Fluids.Mediums_Two.Medium_2,
    precision=2,
    redeclare function iconUnit =
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_psi,
    redeclare function iconUnit2 =
        TRANSFORM.Units.Conversions.Functions.Temperature_K.to_degC)
    annotation (Placement(transformation(extent={{-130,-54},{-150,-34}})));
  TRANSFORM.Fluid.Sensors.PressureTemperature CabRet_pT(
    redeclare package Medium =
        TemplatesCSM.BaseClasses.Fluids.Mediums_Two.Medium_2,
    precision=2,
    redeclare function iconUnit =
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_psi,
    precision2=2)
    annotation (Placement(transformation(extent={{130,-52},{150,-32}})));
  TRANSFORM.Fluid.Sensors.PressureTemperature FacRet_pT(
    redeclare package Medium = Medium_1,
    precision=2,
    redeclare function iconUnit =
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_psi,
    precision2=2) annotation (Placement(transformation(extent={{130,66},{150,86}})));
  TRANSFORM.Fluid.Sensors.PressureTemperature FacSup_pT(
    redeclare package Medium = Medium_1,
    precision=2,
    redeclare function iconUnit =
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_psi,
    precision2=2) annotation (Placement(transformation(extent={{-150,66},{-130,
            86}})));
equation

  connect(resistance_outlet_1.port_b, port_b1)
    annotation (Line(points={{117,60},{180,60}}, color={0,127,255}));

  connect(port_a1, resistance_inlet_1.port_a)
    annotation (Line(points={{-180,60},{-117,60}}, color={0,127,255}));

  connect(resistance_inlet_2.port_b, heatExchanger.port_a1) annotation (Line(
        points={{93,-60},{60,-60},{60,52},{10,52}}, color={0,127,255}));
  connect(tee.port_2, pump.port_a)
    annotation (Line(points={{-70,-60},{-90,-60}}, color={0,127,255}));
  connect(tee.port_1, heatExchanger.port_b1) annotation (Line(points={{-50,-60},
          {-40,-60},{-40,52},{-10,52}}, color={0,127,255}));
  connect(resistance_tank.port_a, tee.port_3)
    annotation (Line(points={{-60,-43},{-60,-50}}, color={0,127,255}));
  connect(resistance_tank.port_b, tank.port)
    annotation (Line(points={{-60,-29},{-60,-18.4}}, color={0,127,255}));
  connect(heatExchanger.port_b2, resistance_outlet_1.port_a)
    annotation (Line(points={{10,60},{103,60}}, color={0,127,255}));
  connect(resistance_inlet_1.port_b, valve.port_a)
    annotation (Line(points={{-103,60},{-80,60}}, color={0,127,255}));
  connect(valve.port_b, heatExchanger.port_a2)
    annotation (Line(points={{-60,60},{-10,60}}, color={0,127,255}));
  connect(controlBus.opening_valve, valve.opening) annotation (Line(
      points={{0,100},{-70,100},{-70,68}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.Nrel_pump, pump.inputSignal) annotation (Line(
      points={{0,100},{-180,100},{-180,-30},{-100,-30},{-100,-53}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.p_CabSup, CabSup_pT.p) annotation (Line(
      points={{0,100},{-180,100},{-180,-41.6},{-146,-41.6}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.T_CabSup, CabSup_pT.T) annotation (Line(
      points={{0,100},{-180,100},{-180,-46.2},{-146,-46.2}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(pump.port_b, port_b2)
    annotation (Line(points={{-110,-60},{-180,-60}}, color={0,127,255}));
  connect(CabSup_pT.port, port_b2) annotation (Line(points={{-140,-54},{-140,-60},
          {-180,-60}}, color={0,127,255}));
  connect(controlBus.p_CabRet, CabRet_pT.p) annotation (Line(
      points={{0,100},{196,100},{196,-39.6},{146,-39.6}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(resistance_inlet_2.port_a, port_a2)
    annotation (Line(points={{107,-60},{180,-60}}, color={0,127,255}));
  connect(CabRet_pT.port, port_a2) annotation (Line(points={{140,-52},{140,-60},
          {180,-60}}, color={0,127,255}));
  connect(FacSup_pT.port, resistance_inlet_1.port_a) annotation (Line(points={{
          -140,66},{-140,60},{-117,60}}, color={0,127,255}));
  connect(FacRet_pT.port, port_b1)
    annotation (Line(points={{140,66},{140,60},{180,60}}, color={0,127,255}));
end v0;
