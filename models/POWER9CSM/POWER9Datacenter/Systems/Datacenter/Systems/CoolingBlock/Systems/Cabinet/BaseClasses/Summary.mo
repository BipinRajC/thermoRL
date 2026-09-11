within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.Cabinet.BaseClasses;
model Summary
  extends TemplatesCSM.BaseClasses.Systems.PartialSummary;

  input Real htc=50.0 "Heat transfer coefficient for air cooling"     annotation(Dialog(group="Inputs"));

end Summary;
