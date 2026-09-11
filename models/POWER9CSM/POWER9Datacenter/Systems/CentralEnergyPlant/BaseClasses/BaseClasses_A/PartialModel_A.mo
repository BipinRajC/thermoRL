within POWER9Datacenter.Systems.CentralEnergyPlant.BaseClasses.BaseClasses_A;
partial model PartialModel_A
  extends BaseClasses.PartialModel;
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (
                                           final port_a, final
      port_b);
end PartialModel_A;
