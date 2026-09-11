within POWER9Datacenter.Systems.CentralEnergyPlant.Tests;
model Test_steady
  extends TemplatesCSM.BaseClasses.Tests.PartialTest_TwoPort_across_pT_pT    (n
      =1, redeclare Models.v0 simulator);
  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Dassl"));
end Test_steady;
