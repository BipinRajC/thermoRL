within POWER9Datacenter.Systems.Datacenter.Systems.CoolingBlock.Systems.CDU.Components;
model LimPID_Deadband_dbr "PID controller with deadband & deadband ratio"
  import InitPID =
         Modelica.Blocks.Types.Init;
  import Modelica.Blocks.Types.Init;
  import Modelica.Blocks.Types.SimpleController;
  extends Modelica.Blocks.Interfaces.SVcontrol;
  parameter SimpleController controllerType=
         SimpleController.PID "Type of controller";
  parameter Boolean derMeas = true "=true avoid derivative kick" annotation(Evaluate=true,Dialog(enable=controllerType==SimpleController.PD or
                                controllerType==SimpleController.PID));
  parameter Real k = 1 "Controller gain: +/- for direct/reverse acting" annotation(Dialog(group="Parameters: Tuning Controls"));
  parameter Modelica.Units.SI.Time Ti(min=Modelica.Constants.small)=0.5
    "Time constant of Integrator block" annotation (Dialog(group="Parameters: Tuning Controls",
        enable=controllerType == SimpleController.PI or controllerType ==
          SimpleController.PID));
  parameter Modelica.Units.SI.Time Td(min=0)=0.1
    "Time constant of Derivative block" annotation (Dialog(group="Parameters: Tuning Controls",
        enable=controllerType == SimpleController.PD or controllerType ==
          SimpleController.PID));
  parameter Real yb = 0 "Output bias. May improve simulation";
  parameter Real k_s = 1 "Setpoint input scaling: k_s*u_s. May improve simulation";
  parameter Real k_m = 1 "Measurement input scaling: k_m*u_m. May improve simulation";
  parameter Real yMax(start=1)=Modelica.Constants.inf "Upper limit of output";
  parameter Real yMin=-yMax "Lower limit of output";
  parameter Real wp(min=0) = 1
    "Set-point weight for Proportional block (0..1)" annotation(Dialog(group="Parameters: Tuning Controls"));
  parameter Real wd(min=0) = 0 "Set-point weight for Derivative block (0..1)"
       annotation(Dialog(group="Parameters: Tuning Controls",enable=controllerType==SimpleController.PD or
                                controllerType==SimpleController.PID));
  parameter Real Ni(min=100*Modelica.Constants.eps) = 0.9
    "Ni*Ti is time constant of anti-windup compensation"
     annotation(Dialog(group="Parameters: Tuning Controls",enable=controllerType==SimpleController.PI or
                              controllerType==SimpleController.PID));
  parameter Real Nd(min=100*Modelica.Constants.eps) = 10
    "The higher Nd, the more ideal the derivative block"
       annotation(Dialog(group="Parameters: Tuning Controls",enable=controllerType==SimpleController.PD or
                                controllerType==SimpleController.PID));
  // Initialization
  parameter .Modelica.Blocks.Types.Init initType=.Modelica.Blocks.Types.Init.NoInit
    "Type of initialization (1: no init, 2: steady state, 3: initial state, 4: initial output)"
    annotation (Evaluate=true, Dialog(tab="Initialization"));
  parameter Real xi_start=0
    "Initial or guess value value for integrator output (= integrator state)"
    annotation (Dialog(tab="Initialization",
                enable=controllerType==SimpleController.PI or
                       controllerType==SimpleController.PID));
  parameter Real xd_start=0
    "Initial or guess value for state of derivative block"
    annotation (Dialog(tab="Initialization",
                         enable=controllerType==SimpleController.PD or
                                controllerType==SimpleController.PID));
  parameter Real y_start=0 "Initial value of output"
    annotation(Dialog(enable=initType == .Modelica.Blocks.Types.Init.InitialOutput,    tab=
          "Initialization"));
  parameter Boolean strict=false "= true, if strict limits with noEvent(..)"
    annotation (Evaluate=true, choices(checkBox=true), Dialog(tab="Advanced"));
  parameter Real deadband = 1
    "if on, and abs(control error) <= deadband, switch off set point tracking"
    annotation (Dialog(group="Hysteresis"));
  parameter Real deadbandRatio = 0.5 "Proportionally change setpoint within deadband operation"
    annotation (Dialog(group="Hysteresis"));
  parameter Boolean pre_y_start=false
    "Value of hysteresis output at initial time"
    annotation (Dialog(group="Hysteresis"));
  TRANSFORM.Controls.LimPID         PID(
    final controllerType=controllerType,
    final k=k,
    final Ti=Ti,
    yb=yb,
    k_s=k_s,
    k_m=k_m,
    final yMax=yMax,
    final yMin=yMin,
    final wp=wp,
    final wd=wd,
    final Ni=Ni,
    final Nd=Nd,
    final initType=initType,
    final xi_start=xi_start,
    final xd_start=xd_start,
    final y_start=y_start,
    final Td=Td,
    final strict=strict)
    annotation (Placement(transformation(extent={{-30,-2},{-10,18}})));
  Modelica.Blocks.Math.RealToBoolean realToBool(threshold=deadband)
    annotation (Placement(transformation(extent={{-8,50},{12,70}})));
  Modelica.Blocks.Math.Feedback feeBac
    annotation (Placement(transformation(extent={{-70,50},{-50,70}})));
  Modelica.Blocks.Math.Gain P(k=deadbandRatio)
    annotation (Placement(transformation(extent={{-10,29},{4,43}})));
  Modelica.Blocks.Math.Add addDbr(k2=+1)
    annotation (Placement(transformation(extent={{16,28},{32,44}})));
  Modelica.Blocks.Math.Abs Abs
    annotation (Placement(transformation(extent={{-36,50},{-16,70}})));
protected
  Modelica.Blocks.Logical.Switch swi1
    annotation (Placement(transformation(extent={{40,50},{60,70}})));
equation
  assert(deadbandRatio <= 1.0 and deadbandRatio >= 0.0, "Require deadbandRatio in [0.0, 1.0].");
  connect(u_m, PID.u_m) annotation (Line(
      points={{-1.11022e-15,-120},{-1.11022e-15,-80},{-20,-80},{-20,-4}},
      color={0,0,127}));
  connect(u_s, feeBac.u1) annotation (Line(
      points={{-120,1.11022e-15},{-80,1.11022e-15},{-80,60},{-68,60}},
      color={0,0,127}));
  connect(u_m, feeBac.u2) annotation (Line(
      points={{-1.11022e-15,-120},{-1.11022e-15,-80},{-60,-80},{-60,52}},
      color={0,0,127}));
  connect(u_s, swi1.u1) annotation (Line(
      points={{-120,1.11022e-15},{-80,1.11022e-15},{-80,80},{20,80},{20,68},{38,
          68}},
      color={0,0,127}));
  connect(swi1.y, PID.u_s) annotation (Line(
      points={{61,60},{94,60},{94,24},{-46,24},{-46,8},{-32,8}},
      color={0,0,127}));
  connect(PID.y, y)
    annotation (Line(points={{-9,8},{94,8},{94,0},{110,0}}, color={0,0,127}));
  connect(u_m, addDbr.u1) annotation (Line(points={{0,-120},{0,-80},{-20,-80},{-20,
          -10},{-60,-10},{-60,46},{8,46},{8,40.8},{14.4,40.8}}, color={0,0,127}));
  connect(P.y, addDbr.u2) annotation (Line(points={{4.7,36},{8,36},{8,31.2},{14.4,
          31.2}}, color={0,0,127}));
  connect(addDbr.y, swi1.u3)
    annotation (Line(points={{32.8,36},{38,36},{38,52}}, color={0,0,127}));
  connect(P.u, feeBac.y) annotation (Line(points={{-11.4,36},{-44,36},{-44,60},{
          -51,60}}, color={0,0,127}));
  connect(realToBool.y, swi1.u2)
    annotation (Line(points={{13,60},{38,60}}, color={255,0,255}));
  connect(realToBool.u, Abs.y)
    annotation (Line(points={{-10,60},{-15,60}}, color={0,0,127}));
  connect(Abs.u, feeBac.y)
    annotation (Line(points={{-38,60},{-51,60}}, color={0,0,127}));
  annotation ( Icon(graphics={
        Polygon(
          points={{-80,94},{-88,72},{-72,72},{-80,94}},
          lineColor={192,192,192},
          fillColor={192,192,192},
          fillPattern=FillPattern.Solid),
        Polygon(
          points={{90,-76},{68,-68},{68,-84},{90,-76}},
          lineColor={192,192,192},
          fillColor={192,192,192},
          fillPattern=FillPattern.Solid),
        Line(points={{-90,-76},{82,-76}}, color={192,192,192}),
        Text(
          extent={{-20,-16},{80,-56}},
          lineColor={192,192,192},
          textString="PID"),
        Line(points={{-80,84},{-80,-84}}, color={192,192,192}),
        Line(points={{-80,-76},{-36,-76},{-36,-30},{36,12},{64,12}}, color={0,0,
              127}),
        Line(points={{-12,73},{-22,68},{-12,63}}),
        Line(points={{-42,68},{28,68}}),
        Line(points={{-22,39},{-12,34},{-22,29}}),
        Line(points={{-42,68},{-42,34}}),
        Line(points={{12,68},{12,34}}),
        Line(points={{-60,34},{12,34}})}),
defaultComponentName="PID",
Documentation(info="<html>
<p>
Block of a controller for set point tracking with a hysteresis element that switches the
controller on and off.
</p>
<p>
If the controller is off, and the control error becomes larger than <code>eOn</code>, then
the controller switches to on and remains on until the control error is smaller than <code>eOff</code>.
When the controller is on, the set point tracking can be done using a P-, PI-, or PID-controller.
In its off-mode, the control output is zero. Thus, the parameters <code>yMin</code> and <code>yMax</code> are
used to constrain the output of the controller during its on mode only. This can be used, for
example, to modulate a device between 0.3 and 1.0, and switch it to off when the control error
is small enough.
</p>
</html>", revisions="<html>
<p>Modified from IBPSA Library</p>
</html>"));
end LimPID_Deadband_dbr;
