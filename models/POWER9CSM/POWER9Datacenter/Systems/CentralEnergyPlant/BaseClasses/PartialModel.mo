within POWER9Datacenter.Systems.CentralEnergyPlant.BaseClasses;
partial model PartialModel
  extends TemplatesCSM.BaseClasses.Systems.PartialModel    (
    redeclare Summary summary,
    redeclare replaceable PartialData data constrainedby PartialData,
    redeclare final ControlBus controlBus,
    redeclare Structure structure,
    redeclare replaceable PartialControls controls constrainedby PartialControls(final structure=structure),
    redeclare replaceable PartialSources sources constrainedby PartialSources(final structure=structure));
end PartialModel;
