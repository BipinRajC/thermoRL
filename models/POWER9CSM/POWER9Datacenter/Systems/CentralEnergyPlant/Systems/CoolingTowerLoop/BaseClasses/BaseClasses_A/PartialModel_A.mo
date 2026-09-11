within POWER9Datacenter.Systems.CentralEnergyPlant.Systems.CoolingTowerLoop.BaseClasses.BaseClasses_A;
partial model PartialModel_A
  extends BaseClasses.PartialModel;
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (
                                           final port_a, final
      port_b);
  extends TemplatesCSM.BaseClasses.Fluids.Interface_TwoPort;
end PartialModel_A;
