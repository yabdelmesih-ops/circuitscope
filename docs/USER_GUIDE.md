# User guide

## Build and solve

Start the app using the README commands. The drawing starts empty. Drag a part
from the inventory, or select its tool and click the canvas. Select the body to
edit values and labels, then press Apply. Values use ohms, volts and amperes;
enter 1000 for 1 kΩ and 0.002 for 2 mA. Use Rotate to turn a selected part.

Drag between terminal circles to connect them. Alternatively, click a starting
terminal, click any desired corners and click the destination terminal. In Wire
mode, click an existing wire to branch through a junction. A crossing alone is
not a connection. Tab flips the bend, Backspace removes a pending corner and
Escape cancels the wire. Include ground before solving.

Choose Find, select the nodes or component, and press Solve drawing. Positive
current follows pin 1 → pin 2; voltage-source pin 1 is positive. A negative
current means flow opposite that reference direction. Negative signed power
means the component supplies energy. Explain node shows conventional current
arrows and KCL notes for a clicked terminal or wire.

## Outputs and examples

An Output probe measures its positive terminal relative to its negative terminal
and draws no current. For open-circuit voltage or Thévenin/Norton analysis,
select only an external load to remove. Keep internal feedback and divider
resistors connected. A disconnected floating node has no unique voltage.

Use the example menus to load reference circuits or the seven Circuits I
examples. Loading an example replaces the drawing. The methods panel works on
supported user-built circuits: supernodes, signed superposition contributions,
source transformations, loaded/unloaded dividers and feedback/summing networks.
A transformed circuit loads only when its load button is pressed. Superposition
adds voltages or currents, never powers.

For op amps, connect +, − and OUT, then choose Negative feedback or Open loop in
the properties. Feedback mode requires a supported passive negative-feedback
path. Open-loop mode chooses a configured output level from the input comparison
and does not force equal inputs. Default limits are −15 V and +15 V.

Save drawing JSON before closing or replacing a circuit; Open a saved drawing
restores it. Clear empties the canvas and Undo restores the last canvas edit.
SPICE export downloads the current circuit or selected port-test configuration.

## Limits

Supported components are resistors, independent DC sources and ideal op amps.
There are no capacitors, inductors, AC/transient calculations, general controlled
sources, hysteresis or physical amplifier models. Unsupported feedback and
closed-loop saturation produce errors. If the app reports no unique solution,
check for floating nodes, incomplete wiring or redundant/conflicting ideal sources.
