within POWER9Datacenter.BaseClasses;
partial model PartialSources
  extends TemplatesCSM.BaseClasses.Systems.PartialSources    (
    redeclare replaceable PartialData data constrainedby PartialData,
    redeclare final ControlBus controlBus,
    redeclare Structure structure);
end PartialSources;
