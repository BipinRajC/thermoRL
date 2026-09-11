within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.BaseClasses.BaseClasses_A;
partial model PartialModel_A
  extends BaseClasses.PartialModel;
  extends
    TemplatesCSM.BaseClasses.Fluids.PartialFourPort_across    (
    final port_a1,
    final port_b1,
    final port_a2,
    final port_b2);

end PartialModel_A;
