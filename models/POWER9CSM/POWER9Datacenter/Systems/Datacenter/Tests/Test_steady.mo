within POWER9Datacenter.Systems.Datacenter.Tests;
model Test_steady
  extends TemplatesCSM.BaseClasses.Tests.PartialTest_TwoPort_across_mT_pT
                                                                       (
      redeclare Models.v0 simulator(
        computeBlock(
          structure(cabinet(each n=3)),
          cabinet(sources(each Q_flow_total=if time < 1000 then 1e3 else 1e4))),
        structure(computeBlock(each n=25))));

  //   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(n=2,
  //       redeclare Models.v0 simulator(
  //         structure(computeBlock(n={2,3})),
  //         computeBlock(
  //           structure(cabinet(n={{2,3},{2,2,3}})),
  //           cabinet(sources(each Q_flow_total=if time < 1000 then 1e3 else 1e4)))));

//   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(n=2,
//       redeclare Models.v0 simulator(structure(computeBlock(n={2,3})),
//         computeBlock(structure(cabinet(n={{2,3},{2,2,3}})), cabinet(sources(
//               Q_flow_total={{{if time < 1000 then 1e3 else 1e4,if time < 1000
//                  then 1e3 else 1e4},{if time < 1000 then 1e3 else 1e3,if time <
//                 1000 then 1e3 else 1e4,if time < 1000 then 1e3 else 1e4}},{{if
//                 time < 1000 then 1e3 else 1e4,if time < 1000 then 1e3 else 1e3},
//                 {if time < 1000 then 1e3 else 1e3,if time < 1000 then 1e3 else 1e4},
//                 {if time < 1000 then 1e3 else 1e2,if time < 1000 then 1e3 else 1e4,
//                 if time < 1000 then 1e3 else 1e2}}})))));

  //   extends ExaDigiT_AutoCSM.BaseClasses.Tests.PartialTest_TwoPort_across(
  //       redeclare Models.v0 simulator(structure={
  //           ORNLSupercomputing.Systems.Datacenter.BaseClasses.Structure(
  //           computeBlock=ExaDigiT_AutoCSM.BaseClasses.Structure(n=structure.computeBlock.nCoolingBlocks))
  //           for i in 1:n}, computeBlock(structure={{
  //             ORNLSupercomputing.Systems.Datacenter.Systems.CoolingBlock.BaseClasses.Structure(
  //             cdu=ExaDigiT_AutoCSM.BaseClasses.Structure(),
  //             cabinet=ExaDigiT_AutoCSM.BaseClasses.Structure(n=structure.computeBlock.nCabinetsPerCoolingBlock))
  //             for i in 1:structure.computeBlocks.nCoolingBlocks} for j in 1:n},
  //           cabinet(sources(Q_flow_total=if time < 1000 then 1e3 else 1e4)))));

  annotation (experiment(
      StopTime=2000,
      __Dymola_NumberOfIntervals=1000,
      __Dymola_Algorithm="Esdirk45a"));
end Test_steady;
