within POWER9Datacenter.Models;
model v0
  extends POWER9Datacenter.BaseClasses.BaseClasses_A.PartialModel_A  (
    redeclare replaceable Controls.NULL controls,
    redeclare replaceable Data.v0 data,
    redeclare replaceable Sources.NULL sources);

  replaceable Systems.Datacenter.Models.v1 datacenter[structure.datacenter.n_int]
    constrainedby Systems.Datacenter.BaseClasses.BaseClasses_A.PartialModel_A(
      redeclare package Medium = Medium)
    annotation (Placement(transformation(extent={{50,-10},{70,10}})));
  replaceable Systems.CentralEnergyPlant.Models.v0 centralEnergyPlant[structure.centralEnergyPlant.n_int]
    constrainedby
    Systems.CentralEnergyPlant.BaseClasses.BaseClasses_A.PartialModel_A(
      redeclare package Medium = Medium)
    annotation (Placement(transformation(extent={{-80,-10},{-60,10}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_outlet_datacenter(
    redeclare package Medium = Medium,
    p_start=datacenter[1].port_b_start.p,
    T_start=datacenter[1].port_b_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_b=structure.centralEnergyPlant.n_int,
    nPorts_a=structure.datacenter.n_int)
    annotation (Placement(transformation(extent={{-10,-50},{10,-30}})));
  TRANSFORM.Fluid.Volumes.MixingVolume plenum_inlet_datacenter(
    redeclare package Medium = Medium,
    p_start=datacenter[1].port_a_start.p,
    T_start=datacenter[1].port_a_start.T,
    redeclare model Geometry =
        TRANSFORM.Fluid.ClosureRelations.Geometry.Models.LumpedVolume.GenericVolume
        (V=0.1),
    nPorts_a=structure.centralEnergyPlant.n_int,
    nPorts_b=structure.datacenter.n_int)
    annotation (Placement(transformation(extent={{10,-10},{-10,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_inlet_datacenter(redeclare package
      Medium = Medium, final nParallel=structure.datacenter.n)
    if structure.datacenter.useParallel
    annotation (Placement(transformation(extent={{20,-10},{40,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_outlet_datacenter(redeclare package
      Medium = Medium, final nParallel=structure.datacenter.n)
    if structure.datacenter.useParallel
    annotation (Placement(transformation(extent={{100,-10},{80,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_outlet_centralEnergyPlant(redeclare
      package Medium = Medium, final nParallel=structure.centralEnergyPlant.n)
    if structure.centralEnergyPlant.useParallel
    annotation (Placement(transformation(extent={{-30,-10},{-50,10}})));
  TRANSFORM.Fluid.Pipes.parallelFlow nFlow_inlet_centralEnergyPlant(redeclare
      package Medium = Medium, final nParallel=structure.centralEnergyPlant.n)
    if structure.centralEnergyPlant.useParallel
    annotation (Placement(transformation(extent={{-110,-10},{-90,10}})));
equation
  connect(centralEnergyPlant.controlBus, controlBus.centralEnergyPlant)
    annotation (Line(
      points={{-70,10},{-70,40},{0,40},{0,100}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(datacenter.controlBus, controlBus.datacenter) annotation (Line(
      points={{60,10},{60,40},{0,40},{0,100}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));

  if structure.datacenter.useParallel then
    connect(plenum_inlet_datacenter.port_b[1], nFlow_inlet_datacenter.port_1);
    connect(nFlow_inlet_datacenter.port_n, datacenter[1].port_a);

    connect(datacenter[1].port_b, nFlow_outlet_datacenter.port_n);
    connect(nFlow_outlet_datacenter.port_1, plenum_outlet_datacenter.port_a[1]);
  else
    connect(plenum_inlet_datacenter.port_b, datacenter.port_a);
    connect(datacenter.port_b, plenum_outlet_datacenter.port_a);
  end if;

  if structure.datacenter.useParallel then
    connect(plenum_outlet_datacenter.port_b[1], nFlow_inlet_centralEnergyPlant.port_1);
    connect(nFlow_inlet_centralEnergyPlant.port_n, centralEnergyPlant[1].port_a);

    connect(centralEnergyPlant[1].port_b, nFlow_outlet_centralEnergyPlant.port_n);
    connect(nFlow_outlet_centralEnergyPlant.port_1, plenum_inlet_datacenter.port_a[1]);
  else
    connect(plenum_outlet_datacenter.port_b, centralEnergyPlant.port_a);
    connect(centralEnergyPlant.port_b, plenum_inlet_datacenter.port_a);
  end if;

end v0;
