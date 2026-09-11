within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Models;
model v1
  extends BaseClasses.BaseClasses_A.PartialModel_A(
    port_b_nominal(p=cdu[1].port_a2_nominal.p, T=cdu[1].port_a2_nominal.T),
    port_a_nominal(
      p=cdu[1].port_a1_nominal.p,
      T=cdu[1].port_a1_nominal.T,
      m_flow=cdu[1].port_a1_nominal.m_flow),
    redeclare replaceable Controls.NULL controls,
    redeclare replaceable Data.NULL data,
    redeclare replaceable Sources.NULL sources);

  replaceable Systems.CDU.Models.v0 cdu[structure.cdu.n_int] constrainedby
    Systems.CDU.BaseClasses.BaseClasses_A.PartialModel_A(redeclare package
      Medium_1 = Medium, redeclare package Medium_2 = Medium)
    "Select CDU model" annotation (Placement(transformation(extent={{-10,-18},{
            10,2}})),
                   choicesAllMatching=true);
  replaceable Systems.Cabinet.Models.v1 cabinet[structure.cabinet.n_int] constrainedby
    Systems.Cabinet.BaseClasses.BaseClasses_A.PartialModel_A(redeclare package
      Medium = Medium) "Select cabinet model" annotation (Placement(
        transformation(extent={{-10,-70},{10,-50}})), choicesAllMatching=true);
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet_cabinet(
    redeclare package Medium = Medium,
    T_start=298.15,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01),
    nPorts_b=structure.cabinet.n_int,
    nPorts_a=structure.cdu.n_int)
    annotation (Placement(transformation(extent={{-70,-70},{-50,-50}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet_cabinet(
    redeclare package Medium = Medium,
    T_start=298.15,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.01),
    nPorts_a=structure.cabinet.n_int,
    nPorts_b=structure.cdu.n_int)
    annotation (Placement(transformation(extent={{50,-70},{70,-50}})));

  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_inlet_cabinet(redeclare package
      Medium = Medium, final nParallel=structure.cabinet.n)
    if structure.cabinet.useParallel
    annotation (Placement(transformation(extent={{-40,-70},{-20,-50}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_outlet_cabinet(redeclare package
      Medium = Medium, final nParallel=structure.cabinet.n)
    if structure.cabinet.useParallel
    annotation (Placement(transformation(extent={{40,-70},{20,-50}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance
                                                      resistance_inlet_cdu(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{-100,-10},{-80,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet_cdu(
    redeclare package Medium = Medium,
    p_start=port_a_start.p,
    T_start=port_a_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_a=1,
    nPorts_b=structure.cdu.n_int)
    annotation (Placement(transformation(extent={{-70,-10},{-50,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_inlet_cdu(redeclare package Medium
      = Medium, final nParallel=structure.cdu.n) if structure.cdu.useParallel
    annotation (Placement(transformation(extent={{-40,-10},{-20,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_outlet_cdu(redeclare package Medium
      = Medium, final nParallel=structure.cdu.n) if structure.cdu.useParallel
    annotation (Placement(transformation(extent={{40,-10},{20,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet_cdu(
    redeclare package Medium = Medium,
    p_start=port_b_start.p,
    T_start=port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_a=structure.cdu.n_int,
    nPorts_b=1)
    annotation (Placement(transformation(extent={{50,-10},{70,10}})));
  TRANSFORM.Fluid.FittingsAndResistances.SpecifiedResistance
                                                      resistance_outlet_cdu(
      redeclare package Medium = Medium, R=
        TRANSFORM.Units.Conversions.Functions.Pressure_Pa.to_Pa(1)/
        port_a_nominal.m_flow)
    annotation (Placement(transformation(extent={{80,-10},{100,10}})));
equation

  if structure.cabinet.useParallel then
    connect(plenum_inlet_cabinet.port_b[1], nFlow_inlet_cabinet.port_1);
    connect(nFlow_inlet_cabinet.port_n, cabinet[1].port_a);

    connect(cabinet[1].port_b, nFlow_outlet_cabinet.port_n);
    connect(nFlow_outlet_cabinet.port_1, plenum_outlet_cabinet.port_a[1]);
  else
    connect(plenum_inlet_cabinet.port_b, cabinet.port_a);

    connect(cabinet.port_b, plenum_outlet_cabinet.port_a);
  end if;

  connect(resistance_inlet_cdu.port_a, port_a)
    annotation (Line(points={{-97,0},{-180,0}}, color={0,127,255}));
  connect(resistance_inlet_cdu.port_b, plenum_inlet_cdu.port_a[1])
    annotation (Line(points={{-83,0},{-66,0}}, color={0,127,255}));
  connect(resistance_outlet_cdu.port_b, port_b)
    annotation (Line(points={{97,0},{180,0}}, color={0,127,255}));
  connect(resistance_outlet_cdu.port_a, plenum_outlet_cdu.port_b[1])
    annotation (Line(points={{83,0},{66,0}}, color={0,127,255}));
  if structure.cdu.useParallel then
    connect(plenum_inlet_cdu.port_b[1], nFlow_inlet_cdu.port_1);
    connect(nFlow_inlet_cdu.port_n, cdu[1].port_a1);

    connect(cdu[1].port_b1, nFlow_outlet_cdu.port_n);
    connect(nFlow_outlet_cdu.port_1, plenum_outlet_cdu.port_a[1]);
  else
    connect(plenum_inlet_cdu.port_b, cdu.port_a1);

    connect(cdu.port_b1, plenum_outlet_cdu.port_a);
  end if;
  connect(cdu.port_b2, plenum_inlet_cabinet.port_a) annotation (Line(points={{-10,-14},
          {-80,-14},{-80,-60},{-66,-60}},      color={0,127,255}));
  connect(plenum_outlet_cabinet.port_b, cdu.port_a2) annotation (Line(points={{66,-60},
          {80,-60},{80,-14},{10,-14}},      color={0,127,255}));
end v1;
