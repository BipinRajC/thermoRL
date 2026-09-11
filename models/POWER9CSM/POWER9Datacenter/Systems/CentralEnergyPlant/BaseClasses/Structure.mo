within POWER9Datacenter.Systems.CentralEnergyPlant.BaseClasses;
record Structure
  extends TemplatesCSM.Icons.Structure;
  parameter TemplatesCSM.Templates.Structure intermediateLoop
    annotation (Placement(transformation(extent={{-30,-6},{-10,14}})));
  parameter TemplatesCSM.Templates.Structure coolingTowerLoop
    annotation (Placement(transformation(extent={{10,-6},{30,14}})));
end Structure;
