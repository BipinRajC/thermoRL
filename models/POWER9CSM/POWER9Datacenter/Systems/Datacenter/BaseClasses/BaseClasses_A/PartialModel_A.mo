within POWER9Datacenter.Systems.Datacenter.BaseClasses.BaseClasses_A;
partial model PartialModel_A
  extends PartialModel;
  extends TemplatesCSM.BaseClasses.Fluids.PartialTwoPort_across    (
                                                            final
      port_a, final port_b);

end PartialModel_A;
