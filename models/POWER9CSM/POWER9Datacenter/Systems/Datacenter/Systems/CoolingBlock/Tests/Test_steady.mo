within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Tests;
model Test_steady

  extends TemplatesCSM.BaseClasses.Tests.PartialTest_TwoPort_across_mT_pT(n=25,
      redeclare Models.v0 simulator(structure(cabinet(each n=3)), cabinet(
          sources(each Q_flow_total=if time < 1000 then 1e3 else 1e4))));

  //   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(n=27,
  //       redeclare Models.v0 simulator(cabinet(sources(Q_flow_total=if time < 1000
  //                then 1e3 else 1e4)), structure(cabinet(n={2 for i in 1:n},
  //             useParallel={if mod(i, 2) == 0 then true else false for i in 1:n}))));

  // Alternative valid approaches
  // Using arrays
  //   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(n=3,
  //       redeclare Models.v0 simulator(cabinet(sources(Q_flow_total=if time < 1000
  //                then 1e3 else 1e4)), structure(cabinet(n={2,2,3},
  //             useParallel={true,false,true}))));

  //Using structures
  //   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(n=27,
  //       redeclare Models.v0 simulator(cabinet(sources(Q_flow_total=if time < 1000
  //                then 1e3 else 1e4)), structure(cabinet={
  //             ExaDigiT_AutoCSM.BaseClasses.Structure(n=2) for i in 1:n})));

  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Esdirk45a"), __Dymola_experimentSetupOutput);
end Test_steady;
