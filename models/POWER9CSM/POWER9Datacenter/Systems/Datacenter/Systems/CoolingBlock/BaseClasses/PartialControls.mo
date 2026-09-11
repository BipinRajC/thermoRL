within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.BaseClasses;
partial model PartialControls
  extends TemplatesCSM.BaseClasses.Systems.PartialControls    (
    redeclare replaceable PartialData data constrainedby PartialData,
    redeclare final ControlBus controlBus,
    redeclare Structure structure);
end PartialControls;
