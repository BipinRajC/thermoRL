within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.IntermediateLoop.Tests;
model Test_steady
  extends TemplatesCSM.BaseClasses.Tests.PartialTest_FourPort_across_pT_pT_pT_pT
                                                                        (
      redeclare Models.v0 simulator);
protected
  BaseClasses.ControlBus controlBus annotation (Placement(
        transformation(extent={{-20,20},{20,60}})));
equation
  connect(controlBus, simulator[1].controlBus) annotation (Line(
      points={{0,40},{0,10}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Dassl"),
      __Dymola_experimentSetupOutput);
end Test_steady;
