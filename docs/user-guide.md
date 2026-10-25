# User guide

## Running the app

```bash
pip install -r requirements.txt
streamlit run drawing_app.py
```

On Windows, `RUN_CIRCUITSCOPE.bat` does the same from the project folder.

The canvas starts empty. Use **Load worked example**, or open **Example circuits and solver checks** to load any of the eleven reference circuits.

## Drawing a circuit

- **Place:** drag a part from the inventory onto the grid, or select a part and click the grid (useful on touchscreens).
- **Move:** in Select / move, drag a component body. Wires follow its pins, and the part snaps to the grid on release. Esc cancels a drag.
- **Wire by dragging:** press on a terminal, drag to another, and release when the green target ring appears.
- **Wire by clicking:** click a start terminal, click empty grid points to add corners, then click an end terminal or an existing wire. Tab (or **Flip bend**) switches the next elbow. Backspace removes the last corner.
- **Branch:** in Wire mode, start or end on an existing wire. A junction dot is inserted and the wire is split.
- **Cancel a wire:** Esc, right-click, or **Cancel wire**. Nothing is added to the circuit.
- **Ground:** every circuit needs at least one ground symbol. All ground symbols are node 0.
- **Rotate:** select a part and press **Rotate** or R.
- **Edit:** select a part, change its value or node labels, and click **Apply**. Op amps also have an **Op-amp operation** setting (feedback or open-loop comparator) and output minimum/maximum fields. For a comparator, those limits are its LOW and HIGH output levels.
- **Delete / Undo / Clear:** Delete removes the selected part (and its wires) or wire. Undo reverts any drawing edit, including Clear.
- **Save / open:** **Save drawing JSON** downloads the drawing. Open it again from **Open a saved drawing**. The canvas can reset when the server restarts, so save anything you want to keep.

**Crossing lines do not connect.** Connections exist only between explicitly wired terminals or at junction dots. Placing two terminals at the same position does not connect them.

Optional node labels (such as `Va`) name a node. Use a ground symbol rather than typing `0`.

## Conventions

- R, V and I terminals are pin 1 and pin 2. Positive branch current flows from pin 1 to pin 2.
- A voltage source is positive at pin 1 relative to pin 2.
- An op amp has + (pin 1), − (pin 2) and OUT (pin 3). Positive op-amp current flows into OUT. Input currents are zero.
- An output probe has + and − terminals with no internal connection.
- Positive power means a component absorbs energy. Values use ohms, volts and amperes.

## Asking a question

Choose a question in **Find**, select the nodes, component or load, and click **Solve drawing**:

| Question | Inputs |
|---|---|
| Node voltage | Two nodes; the answer is V(first) − V(second) |
| Open-circuit voltage | An output probe or two nodes, and an optional external load to remove |
| Branch current / Component power | One component |
| Thévenin / Norton | Two port nodes and an optional load to remove |

Removing a load affects only that calculation. The canvas shows the load as OPEN, and the saved drawing is unchanged. Thévenin and Norton are unavailable when the circuit contains a comparator, because a switching output has no linear equivalent.

## Op-amp modes

- **Feedback:** connect OUT back to − directly or through resistors. The amplifier holds V+ = V− while its output stays within its limits.
- **Open loop (comparator):** wire + to the signal and − to the reference, with no path from OUT back to either input. OUT takes the HIGH level when V+ > V− and the LOW level when V+ < V−. Equal inputs are reported as undefined.

Try **Open loop · comparator HIGH (5 V)** from the examples. Changing V1 from 3 V to 1 V switches the output LOW, and setting it to 2 V (equal to the reference) shows the undefined-decision message. See [op-amp-model.md](op-amp-model.md).

## Click-to-explain lessons

Choose **Explain node** in the inventory (or press E), then click any terminal or wire. The node is solved relative to ground and explained in four steps:

1. **Node:** every wire and terminal in that electrical node is highlighted in purple.
2. **Current:** numbered arrows show conventional current through each connected component. Orange enters the node, green leaves.
3. **KCL:** the node equation is written symbolically from the connected parts, then solved. Coupled nodes show the full simultaneous system.
4. **Check:** entering and leaving currents are compared, with the numerical residual.

Editing values, wiring or the question hides old results until you solve again. Moving parts keeps the lesson, since position doesn't affect the circuit.

## Guided practice

Open **Guided practice · predict, check, explain** to work nine questions with hints and graded answers. See [guided-practice.md](guided-practice.md).

## Exporting to SPICE

Open **Export for LTspice / ngspice**, choose the format and either **Full drawing** or **Current solved circuit**, then click **Prepare SPICE export** and **Download SPICE netlist**. Enable **Show exported netlist and node names** to see the file and how its node names map to your labels. **Show independent SPICE verification**, under the examples, displays the committed ngspice validation report. See [spice-validation.md](spice-validation.md).

## Error messages

The app reports missing ground, floating nodes, invalid values, conflicting labels, shorted voltage sources, feedback op amps without negative feedback, comparators with feedback or equal inputs, and outputs that would saturate. Other singular configurations, such as conflicting ideal sources, are reported as having no unique DC solution.

## Scope

Supported: resistors, independent ideal DC voltage and current sources, ideal op amps with direct or resistive negative feedback, and ideal two-level open-loop comparators (up to eight per drawing). Not supported: capacitors, inductors, dependent sources, AC, transients, hysteresis, closed-loop saturation, and real op-amp imperfections.
