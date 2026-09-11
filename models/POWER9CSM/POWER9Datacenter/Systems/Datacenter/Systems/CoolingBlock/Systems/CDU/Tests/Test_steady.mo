within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Tests;
model Test_steady
  extends
    TemplatesCSM.BaseClasses.Tests.PartialTest_FourPort_across_pT_pT_pT_pT    (
      redeclare Models.v0 simulator);
  annotation (
    Icon(coordinateSystem(preserveAspectRatio=false)),
    Diagram(coordinateSystem(preserveAspectRatio=false)),
    experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Dassl"));
end Test_steady;
