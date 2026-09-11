within POWER9Datacenter.Tests;
model Test_dynamic
  extends Test_steady(simulator(centralEnergyPlant(coolingTowerLoop(sources(
              each T_ext=data_external.y[2]*T_delta + T_min))), datacenter(computeBlock(
            cabinet(sources(each Q_flow_total=data_external.y[1]*Q_delta + Q_min))))));

 parameter Real T_min = 15+273.15;
 parameter Real T_delta = 6;

 parameter Real Q_min = 5e3;
 parameter Real Q_delta = 1e4;

  Modelica.Blocks.Sources.CombiTimeTable data_external(
    tableOnFile=true,
    tableName="table",
    fileName=Modelica.Utilities.Files.loadResource(
        "modelica://POWER9Datacenter/../../data/example_timeseries_scaled.txt"),
    columns={2,3},
    extrapolation=Modelica.Blocks.Types.Extrapolation.HoldLastPoint)
    annotation (Placement(transformation(extent={{-60,20},{-40,40}})));
  annotation (experiment(
      StopTime=86400,
      __Dymola_NumberOfIntervals=8640,
      __Dymola_Algorithm="Sdirk34hw"));
end Test_dynamic;
