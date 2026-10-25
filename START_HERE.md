# CircuitScope: add the drawing canvas

This complete project extends your Python solver with ideal feedback op amps and open-circuit voltage measurements. It includes nine worked circuits, solver checks, the drawing canvas and click-to-explain lessons. Keep all extracted files together; the updated engine uses circuit_model.py.

## Update an existing installation

This complete ZIP includes the updated engine.py and every app module. Extract it, stop the old Streamlit server with Ctrl+C, open the new folder in VS Code and run **py -m streamlit run drawing_app.py**. The files sit directly in the extracted folder. Refresh the browser with Ctrl+F5 after restarting. You can also try the included Windows launcher.

## Set up

1. Extract the ZIP.
2. The updated **engine.py** is already included beside **drawing_app.py**. Keep the extracted files together.
3. Open the extracted folder in VS Code. Its contents should include:

```
circuitscope-canvas/
    engine.py             <- extended numerical solver, included
    circuit_model.py      <- common branch and feedback conventions
    opamp_examples.py     <- amplifier and open-output examples
    drawing_app.py
    topology.py
    teaching.py           <- node explanations and current directions
    examples.py           <- drawn examples and fixed reference answers
    verification.py       <- hand-answer, KCL and power checks
    requirements.txt
    sample_drawing.json
    canvas/
        editor.html
        editor.css
        editor.js
```

4. If the old Streamlit server is occupying your terminal, press **Ctrl+C**. In a terminal opened in this extracted folder, run:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run drawing_app.py
```

Open the Local URL shown in the terminal. Your older scripts can remain in their original folder.

On Windows you can also double-click **RUN_CIRCUITSCOPE.bat** in the folder containing drawing_app.py. The launcher uses that folder automatically, including paths with spaces.

## Try the new op amps and open outputs

Open **Op-amp material** for the ideal rules and gain derivations. In **Example circuits and solver checks**, load **Op amp · inverting amplifier (−2 V)**. Choose **Open-circuit voltage**, select **OUT1**, choose **RL** as the load to remove, then **Solve drawing**. Expected: **−2 V**. The canvas displays RL as OPEN for this calculation; RL stays in your saved drawing. Rf remains connected and still carries feedback current.

Load the **voltage follower** example to see **2 V** with zero output current, or **Open output · 12 V with no resistor current** to see why voltage does not require load current. Drag your own **Output probe** onto the canvas, wire + to the desired node and − to a reference, and use the same question. Select **None** for the load if the output is already unloaded. A disconnected probe end reports an undefined voltage.

The new ZIP is a complete folder update: use its updated engine and canvas together. Your older saved R/V/I drawings still load.

## First check

Open **Example circuits and solver checks**. Select one of the nine examples and click **Load selected example**. You can enable **Show this example’s hand-calculated reference** to see its equations. **Run solver checks** checks all nine examples through your engine.py without changing your active drawing. The result table reports voltage, branch-current, KCL, signed-power and Thévenin/Norton comparisons. If engine.py changes, its old check report is hidden until checks are run again.

See **REFERENCE_CASES.md** for the expected values and remaining validation work. These checks use independently worked equations; external SPICE comparison and real-browser interaction checks still remain.

The canvas opens empty so you can build your own circuit. Click **Clear screen / New circuit** above the canvas to remove all components and wires and start again. Save a drawing first if you want to keep it.

To check the solver, click **Load worked example** to load the circuit we already solved:

- Source V1 = 12 V, positive node Vb.
- R1 = 1000 ohms between Vb and Va.
- R2 = 1000 ohms between Va and ground.
- R3 = 2000 ohms between Va and Vb.

Choose **Node voltage**, first node **Va**, second node **0**, then **Solve drawing**. Expected: **7.2 V**.

Keep **Teach me how this node works** enabled to turn that answer into a visual lesson. The question controls are above the canvas. After solving, switch between **Node**, **Current**, **KCL**, and **Check**:

**Click-to-explain shortcut:** choose **Explain node** in the inventory, or press **E** while the canvas has focus. Click a terminal circle or any wire to solve and explain that node relative to ground immediately. Wire clicks use the node at that wire's endpoints. Explain mode stays active so you can explore several nodes. Ground and junction symbols can also be clicked directly. For a two-terminal component, click the specific end you want. **Esc** returns to Select / move. These clicks select a question without adding wires or moving parts. Incomplete circuits report the missing connection or ground instead of showing a misleading answer.

- **Node:** purple highlights every wired terminal and wire in the selected electrical node. Its voltage is measured relative to ground.
- **Current:** numbered arrows through components show conventional current in the computed direction. Notes beside the drawing explain each connected branch. Orange enters the selected node; green leaves; gray shows other branches. Electron motion in metal is opposite the arrows. These are steady-state arrows, not a simulation of charge speed.
- **KCL:** the selected-node equation is built from the actual connected parts. Resistor terms use (selected voltage − neighbor voltage)/R. Only source-fixed voltages count as givens. Coupled unknowns and floating voltage sources are explained using the full simultaneous equation set.
- **Check:** entering and leaving currents are compared, with a numerical residual. Ground remains a reference; it does not consume current.

For Va in the example, R1 carries **4.8 mA into Va**, R3 carries **2.4 mA into Va**, and R2 carries **7.2 mA out**. The currents balance. R3's pin-1-to-pin-2 current is negative, so its arrow reverses.

Lessons persist when changing the step or moving parts. Changing values, wiring, the selected question or reference hides old answers until you solve again. The editor hides local annotations immediately after an edit while waiting for Python. Individual ideal-wire currents are not assigned: the arrows label component branch currents, while wires highlight node connectivity.

For **Thevenin**, use the same port and remove **R2**. Expected: **12 V** and **666.666667 ohms**.

For **Norton**, remove R2. Expected: **0.018 A** and **666.666667 ohms**.

## Draw your own circuit

- **Place:** drag a component from inventory. Alternatively, choose a part and click the grid; this is useful on touchscreens.
- **Move:** choose Select / move, then drag a component body. Wires follow its pins. Movement is continuous during the drag and snaps to the grid when released. Escape cancels a drag.
- **Wire by dragging:** press on a terminal, drag to another terminal and release when its green target ring appears. Nearby releases snap to the target. The wire is saved only when finished.
- **Wire by clicking:** click the start terminal, click empty grid locations for corners, then click an end terminal or existing wire. Tab or **Flip bend** switches the next elbow. Backspace or Undo removes the last unfinished corner. Wire mode (button or W) stays active after completion so you can continue adding wires. Starting directly from a terminal in Select / move returns to Select / move when finished.
- **Branch:** in Wire mode, click an existing wire as a start or end. Finishing inserts a visible junction dot and splits that wire into connected segments. The branch is one undoable edit; cancelling creates no dot or half wire. Explicit junction dots and several connections to the same terminal still work.
- **Cancel:** Escape, right-click or **Cancel wire** discards an unfinished wire. Select / move is then active. The circuit is not changed. A lost pointer capture also cancels a dragged wire safely.
- **Ground:** connect a ground symbol. All ground symbols represent node 0.
- **Rotate:** select a component and press Rotate, or R while the canvas has focus.
- **Edit:** select a component, change its value or optional node labels, then Apply.
- **Remove:** select a component body or wire and use Delete. Removing a component removes wires attached to it.
- **Undo:** reverts drawing edits, including Clear.
- **Save:** use Save drawing JSON before closing or loading a different project. The file includes components, positions, wires, and node labels. Open it through the saved-drawing expander.

R/V/I pins are numbered **1** and **2**. A voltage source is positive at pin 1 relative to pin 2. Their positive branch current flows 1 to 2. An op amp has **+ (1)**, **− (2)** and **OUT (3)**; its positive current enters OUT, and both input currents are zero. A probe has **+ (1)** and **− (2)** with no internal connection. Positive branch power means absorption; amplifier output power uses implicit supply/ground returns.

**Crossing lines do not connect.** Electrical connections exist only between explicitly wired terminals. A deliberate start/end on an existing wire creates a junction dot. A line merely passing over another wire or terminal makes no connection. Simply moving two terminals onto the same position does not wire them together. This rule keeps moving components from silently changing the circuit's topology.

Wire corners are saved in the drawing JSON as routing points. They affect the picture, while terminal IDs determine the electrical connections. Existing saved drawings with automatic elbows still load. Manual routes retain their corners and reconnect to terminal positions when components move.

Optional labels name a node, such as Va. A wire connecting differently labeled nodes creates a conflict; select a component and clear one label to resolve it. Use a ground symbol, rather than a typed 0 label, to create ground.

The canvas state survives normal Streamlit reruns during a live session. Revision numbers protect newer local edits from delayed backend responses. Property text being edited is retained across re-renders. A new browser session or server restart can reset the canvas, so use the JSON download for a durable project copy.

## What runs where?

1. **canvas/editor.js** manages dragging, symbols and explicit wires. It sends a drawing object to Python through Streamlit's custom-component interface.
2. **topology.py** follows the wires to decide which pins share a node, then creates the component dictionaries.
3. **engine.py** extends your modified nodal analysis solver. It generates equations and solves them with NumPy, including zero input currents and a feedback voltage constraint for ideal op amps.
4. **drawing_app.py** connects those pieces and displays the answer.

Open **See what the drawing sends to your solver** to watch the component list change. R/V/I keep the `name`, `type`, `node1`, `node2`, `value` structure you used in the terminal. Op amps add `node3` for OUT and output limits. Probes add no solver branch.

Read **HOW_IT_WORKS.md** for the code walkthrough.

## Scope

Resistors, independent ideal DC voltage/current sources, and ideal op amps with direct or passive resistive negative feedback. Node voltages, open-circuit outputs, branch currents, component power, Thevenin and Norton are available. Visual teaching explains node and open-output questions. Ideal amplifier outputs have zero resistance, so the app correctly rejects a finite Norton current there. Capacitors, inductors, general dependent sources, AC, transients, comparators, saturation and real op-amp imperfections remain outside scope. Read **OPAMPS_AND_OUTPUTS.md** for the assumptions and code changes.

The app catches missing ground, loose/floating nodes, invalid values and conflicting node labels. Other singular ideal-source configurations are reported by NumPy through the app's error message. This is an educational linear-circuit tool, not an externally SPICE-validated simulator.

## Verification

Automated checks cover topology, worked numerical answers, Python UI calculation paths, geometry, pin wiring, property edits and undo. A real Streamlit AppTest checks component registration, empty startup, the sample solve and clearing when Streamlit is installed. JavaScript tests include a lightweight harness and a real SVG DOM through jsdom. DOM checks verify that movement retains existing SVG elements, coalesces mouse events into animation frames, publishes once on release, previews wires, cancels drags, retains property drafts and rejects stale backend responses. These checks do not verify actual browser layout, native hit testing, native drag-and-drop or the real browser-to-Streamlit transport. Those browser checks remain to be performed on your machine.

To run developer tests, install requirements.txt for Python and use a current Node.js version with npm:

```powershell
py -m unittest discover -s tests -v
npm install
npm test
```

`tests/reference_engine.py` re-exports the bundled engine for UI and lesson checks. The answer keys are independent fixed hand calculations in the example modules. The app itself imports your `engine.py` at the project root.

Streamlit's official component documentation:
https://docs.streamlit.io/develop/concepts/custom-components/components-v2/register

Teaching reference (KCL, current signs and energy):
https://openstax.org/books/university-physics-volume-2/pages/10-3-kirchhoffs-rules
https://docs.streamlit.io/develop/concepts/custom-components/components-v2/examples
