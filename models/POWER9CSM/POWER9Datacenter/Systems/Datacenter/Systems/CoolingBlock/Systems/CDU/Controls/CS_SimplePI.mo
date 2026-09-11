within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Controls;
model CS_SimplePI
  extends BaseClasses.PartialControls(redeclare replaceable Data.NULL
      data);

  TRANSFORM.Controls.LimPID
    PID_valve(
    controllerType=Modelica.Blocks.Types.SimpleController.PI,
    k=-0.1,
    Ti=50,
    yMax=1,
    yMin=0.01,
    initType=Modelica.Blocks.Types.Init.InitialOutput,
    y_start=0.5)          annotation (Placement(transformation(
          extent={{-10,30},{10,50}})));
  TRANSFORM.Controls.LimPID PID_pump(
    controllerType=Modelica.Blocks.Types.SimpleController.PI,
    k=0.1,
    Ti=100,
    yMax=2,
    yMin=0.01,
    initType=Modelica.Blocks.Types.Init.InitialOutput,
    y_start=0.5)
    annotation (Placement(transformation(extent={{-10,-30},{10,-10}})));
  Modelica.Blocks.Sources.RealExpression T_setpoint(y=40 + 273.15)
    annotation (Placement(transformation(extent={{-40,30},{-20,50}})));
  Modelica.Blocks.Math.Add dP(k1=-1, k2=+1)
    annotation (Placement(transformation(extent={{10,-10},{-10,10}},
        rotation=180,
        origin={-30,-50})));
  Modelica.Blocks.Sources.RealExpression dp_setpoint(y=2e5)
    annotation (Placement(transformation(extent={{-40,-30},{-20,-10}})));
  Modelica.Blocks.Sources.Constant opening_valve(k=0.5)
                         annotation (Placement(transformation(
          extent={{20,52},{40,72}})));
equation
  connect(controlBus.T_CabSup, PID_valve.u_m) annotation (Line(
      points={{0,-100},{-100,-100},{-100,20},{0,20},{0,28}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(T_setpoint.y, PID_valve.u_s)
    annotation (Line(points={{-19,40},{-12,40}}, color={0,0,127}));
  connect(controlBus.p_CabSup, dP.u2) annotation (Line(
      points={{0,-100},{-100,-100},{-100,-44},{-42,-44}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.p_CabRet, dP.u1) annotation (Line(
      points={{0,-100},{-100,-100},{-100,-56},{-42,-56}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(dP.y, PID_pump.u_m)
    annotation (Line(points={{-19,-50},{0,-50},{0,-32}}, color={0,0,127}));
  connect(dp_setpoint.y, PID_pump.u_s)
    annotation (Line(points={{-19,-20},{-12,-20}}, color={0,0,127}));
  connect(controlBus.Nrel_pump, PID_pump.y) annotation (Line(
      points={{0,-100},{100,-100},{100,-20},{11,-20}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
  connect(controlBus.opening_valve, PID_valve.y) annotation (Line(
      points={{0,-100},{112,-100},{112,0},{32,0},{32,40},{11,40}},
      color={255,215,136},
      pattern=LinePattern.Dash,
      thickness=0.5));
end CS_SimplePI;
