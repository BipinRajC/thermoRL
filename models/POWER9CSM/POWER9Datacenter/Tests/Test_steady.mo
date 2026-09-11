within POWER9Datacenter.Tests;
model Test_steady
  extends TemplatesCSM.BaseClasses.Tests.PartialTest    (n=1, redeclare
      Models.v0 simulator(datacenter(structure(computeBlock(each n=25)),
          computeBlock(structure(cabinet(each n=3)), cabinet(sources(each
                Q_flow_total=if time < 1000 then 1e3 else 1e4))))));

protected
  BaseClasses.ControlBus controlBus
    annotation (Placement(transformation(extent={{-20,20},{20,60}})));
equation
  connect(simulator[1].controlBus, controlBus) annotation (Line(
      points={{0,10},{0,40}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Sdirk34hw"));
end Test_steady;
